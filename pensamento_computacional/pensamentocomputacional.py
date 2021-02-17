from quiz_stats import QuizStatsXBlock
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Scope, UserScope, BlockScope, ScopeBase
from xblock.fields import String, Dict
from common.djangoapps.student.models import user_by_anonymous_id, get_user_by_username_or_email, CourseEnrollment
from django.core.exceptions import PermissionDenied
from xblockutils.resources import ResourceLoader
from openedx.core.djangoapps.course_groups.cohorts import get_cohort, is_course_cohorted, get_course_cohorts
from webob.response import Response
import json
import pkg_resources
from submissions import api as submissions_api

loader = ResourceLoader(__name__)
PROFS_COHORT = "professores"


def resource_string(path):
    """Handy helper for getting resources from our kit."""
    data = pkg_resources.resource_string(__name__, path)
    return data.decode("utf8")


class PensamentoComputacionalXBlock(QuizStatsXBlock):
    display_name = String(display_name="display_name",
                          default="Pensamento Computacional Stats",
                          scope=Scope.settings,
                          help="Nome do componente na plataforma")

    has_author_view = True

    # ----------- Views -----------
    def author_view(self, _context):
        if not is_course_cohorted(self.course_id) or PROFS_COHORT not in super().get_cohorts():
            return Fragment("Turmas têm que estar ativas e tem que existir uma turma chamada \"professores\"")
        data = {
            'xblock_id': self._get_xblock_loc()
        }
        html = loader.render_django_template('templates/author_view.html', data)
        frag = Fragment(html)
        frag.add_css(resource_string("static/css/profs_assignment.css"))
        frag.add_javascript(resource_string("static/js/turmas_assignment.js"))
        frag.initialize_js('PensamentoComputacionalXBlock', data)
        return frag

    def student_view(self, _context):
        if self.invalid_cohort():
            self.cohort = self.default_cohort
        if self.invalid_cohort():  # no valid cohort for this user
            return Fragment("Ainda não lhe foi atribuída uma turma!")
        return super().student_view(_context)

    @XBlock.json_handler
    def change_cohort(self, data, _suffix):
        if data["cohort"] in self.get_cohorts():
            self.cohort = data["cohort"]
            return {
                'result': 'success'
            }
        raise PermissionDenied

    @XBlock.json_handler
    def remove_turma(self, data, _suffix):
        turma = data["turma"]
        prof = str(data["prof_id"])
        turmas_professores = self.turmas_professores
        if turma in turmas_professores[prof]:
            turmas_professores[prof].remove(turma)
            self.save_turmas_professores(turmas_professores)
            return {
                'result': 'success'
            }
        return {
            'result': 'error'
        }

    @XBlock.json_handler
    def add_turma(self, data, _suffix):
        turma = data["turma"]
        prof = str(data["prof_id"])
        turmas_professores = self.turmas_professores
        if turma not in turmas_professores[prof] and turma in super().get_cohorts():
            turmas_professores[prof].append(turma)
            self.save_turmas_professores(turmas_professores)
            return {
                'result': 'success'
            }
        return {
            'result': 'error'
        }

    @XBlock.handler
    def load_assignment_data(self, request, suffix=''):
        enrollments = CourseEnrollment.objects.filter(course_id=self.course_id)
        names = {}
        turmas_professores = self.turmas_professores
        needs_save = False
        for enr in enrollments:
            cohort = get_cohort(enr.user, self.course_id, assign=False, use_cached=True)
            if cohort and cohort.name == PROFS_COHORT:  # add missing profs
                user_id = str(enr.user.id)
                if user_id not in turmas_professores:
                    turmas_professores[user_id] = []
                    needs_save = True
                names[user_id] = enr.user.username
                if enr.user.profile.name:
                    names[user_id] = self.format_name(enr.user.profile.name)

        # clean up "old" teachers
        for prof in list(turmas_professores.keys()):
            if prof not in names:
                del turmas_professores[prof]
                needs_save = True
        if needs_save:
            self.save_turmas_professores(turmas_professores)
        return Response(json.dumps({
            'turmas_profs': turmas_professores,
            'turmas': super().get_cohorts(),
            'nomes': names
        }))

    def get_cohorts(self):
        if super().is_staff:
            return super().get_cohorts()
        turmas_professores = self.turmas_professores
        return turmas_professores[str(self.user_id)] if str(self.user_id) in turmas_professores else []

    @property
    def is_staff(self):
        cohort = get_cohort(user_by_anonymous_id(self.xmodule_runtime.anonymous_student_id), self.course_id,
                            assign=False, use_cached=True)
        return super().is_staff or (cohort and cohort.name == PROFS_COHORT)

    @property
    def user_id(self):
        return user_by_anonymous_id(self.xmodule_runtime.anonymous_student_id).id

    def invalid_cohort(self):
        return self.cohort not in self.get_cohorts()

    @property
    def default_cohort(self):
        cohorts = self.get_cohorts()
        if cohorts:
            return cohorts[0]
        return ""

    @property
    def turmas_professores(self):
        try:
            subs = submissions_api.get_submissions(self.get_student_item_dict())
        except submissions_api.SubmissionNotFoundError:
            return {}
        if len(subs) > 0:
            return subs[0]['answer']
        return {}

    def save_turmas_professores(self, data):
        submissions_api.create_submission(self.get_student_item_dict(), data, attempt_number=1)

    def get_student_item_dict(self):
        # pylint: disable=no-member
        """
        Returns dict required by the submissions app for creating and
        retrieving submissions for a particular student.
        """
        return {
            "student_id": "TURMAS_PROFESSORES2",
            "course_id": self.block_course_id(),
            "item_id": "TURMAS_PROFESSORES",
            "item_type": "TURMAS_PROFESSORES",
        }
