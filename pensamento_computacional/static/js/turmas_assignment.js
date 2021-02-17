function PensamentoComputacionalXBlock(runtime, element, context) {
    function xblock($, _) {
        let template = _.template($(element).find("#pensamento_comp_turmas_temp_" + context.xblock_id).text());
        const load_assignment_data_url = runtime.handlerUrl(element, 'load_assignment_data').replace("/preview", "");
        const remove_turma_url = runtime.handlerUrl(element, 'remove_turma').replace("/preview", "");
        const add_turma_url = runtime.handlerUrl(element, 'add_turma').replace("/preview", "");

        function loadData(){
            $.get(load_assignment_data_url, function (data) {
                render(data);
            });
        }

        function render(data) {
            console.log(data)
            let content_el = $(element).find('#pensamento_comp_turmas_' + context.xblock_id);
            // Render template
            content_el.html(template(data));
            // handlers
            $('.turma-remove-select_' + context.xblock_id).on('change', function () {
                const prof_id = $(this).closest('tr').data('prof_id');
                const prof_name = data.nomes[prof_id];
                const turma = $(this).val();
                if (confirm("De certeza que quer remover a turma \"" + turma + "\" do professor \"" + prof_name + "\"")){
                    $.post(remove_turma_url, JSON.stringify({
                        'turma': turma,
                        'prof_id': prof_id,
                    }), (res) => {
                        if(res.result === "success") {
                            data.turmas_profs[prof_id] = data.turmas_profs[prof_id].filter(item => item !== turma);
                            render(data)
                        } else
                            $(this).val("")
                    });
                } else
                    $(this).val("")
            });
            $('.turma-add-select_' + context.xblock_id).on('change', function () {
                const prof_id = $(this).closest('tr').data('prof_id');
                const prof_name = data.nomes[prof_id];
                const turma = $(this).val();
                if (confirm("De certeza que quer adicionar a turma \"" + turma + "\" ao professor \"" + prof_name + "\"")) {
                    $.post(add_turma_url, JSON.stringify({
                        'turma': turma,
                        'prof_id': prof_id,
                    }), (res) => {
                        if (res.result === "success") {
                            data.turmas_profs[prof_id].push(turma);
                            render(data)
                        } else
                            $(this).val("")
                    });
                } else
                    $(this).val("")
            });
        }

        $(function () {
            loadData();
        });
    }
    function loadjs(url) {
        $('<script>')
            .attr('type', 'text/javascript')
            .attr('src', url)
            .appendTo(element);
    }

    if (require === undefined) {
        /**
         * The LMS does not use require.js (although it loads it...) and
         * does not already load jquery.fileupload.  (It looks like it uses
         * jquery.ajaxfileupload instead.  But our XBlock uses
         * jquery.fileupload.
         */
        loadjs('/static/js/vendor/jQuery-File-Upload/js/jquery.iframe-transport.js');
        loadjs('/static/js/vendor/jQuery-File-Upload/js/jquery.fileupload.js');
        xblock($, _);
    } else {
        /**
         * Studio, on the other hand, uses require.js and already knows about
         * jquery.fileupload.
         */
        require(['jquery', 'underscore', 'jquery.fileupload'], xblock);
    }
}
