package br.ufpi.agenda
{
    import mx.rpc.events.FaultEvent;
    import mx.rpc.events.ResultEvent;
    import mx.rpc.http.HTTPService;

    /**
     * Cliente da API REST de contatos usando mx.rpc.http.HTTPService + JSON nativo (Flash Player 11+).
     *
     * Contornos para limitações do Flash Player:
     *  - PUT/DELETE: envia POST com ?_method=PUT|DELETE (o backend faz o "method override").
     *  - Erros 4xx/5xx: o Flash não expõe o corpo da resposta de erro, então todas as chamadas levam
     *    ?suppress_response_codes=true e o backend devolve 200 com {"erro": "..."}.
     *  - POST sem corpo vira GET no Flash, por isso o DELETE envia "{}".
     *  - Cache de GET no navegador: parâmetro _ts com o horário atual.
     */
    public class ApiClient
    {
        private var baseUrl:String;

        /** @param baseUrl URL base da API, ex.: "api" (mesma origem via nginx) ou "http://localhost:8081/api". */
        public function ApiClient(baseUrl:String)
        {
            this.baseUrl = baseUrl;
        }

        public function listar(filtro:String, ok:Function, falha:Function):void
        {
            var extra:String = (filtro != null && filtro.length > 0) ? "&q=" + encodeURIComponent(filtro) : "";
            chamar("GET", "/contatos", extra, null, ok, falha);
        }

        public function buscar(id:Number, ok:Function, falha:Function):void
        {
            chamar("GET", "/contatos/" + id, "", null, ok, falha);
        }

        public function criar(contato:Object, ok:Function, falha:Function):void
        {
            chamar("POST", "/contatos", "", contato, ok, falha);
        }

        public function atualizar(contato:Object, ok:Function, falha:Function):void
        {
            chamar("PUT", "/contatos/" + contato.id, "", contato, ok, falha);
        }

        public function excluir(id:Number, ok:Function, falha:Function):void
        {
            chamar("DELETE", "/contatos/" + id, "", {}, ok, falha);
        }

        private function chamar(metodo:String, caminho:String, extra:String, corpo:Object,
                                ok:Function, falha:Function):void
        {
            var url:String = baseUrl + caminho
                + "?suppress_response_codes=true&_ts=" + new Date().time + extra;

            var servico:HTTPService = new HTTPService();
            servico.useProxy = false;
            servico.resultFormat = HTTPService.RESULT_FORMAT_TEXT;
            servico.requestTimeout = 30;

            if (metodo == "GET")
            {
                servico.method = "GET";
            }
            else
            {
                servico.method = "POST";
                servico.contentType = "application/json";
                if (metodo != "POST")
                {
                    url += "&_method=" + metodo;
                }
            }
            servico.url = url;

            servico.addEventListener(ResultEvent.RESULT, function(e:ResultEvent):void
            {
                var texto:String = e.result != null ? String(e.result) : "";
                var dados:Object = null;
                try
                {
                    dados = texto.length > 0 ? JSON.parse(texto) : null;
                }
                catch (erro:Error)
                {
                    falha("Resposta inválida do servidor: " + texto.substr(0, 200));
                    return;
                }
                if (dados != null && !(dados is Array) && dados.hasOwnProperty("erro"))
                {
                    var msg:String = String(dados.erro);
                    if (dados.hasOwnProperty("detalhes") && dados.detalhes is Array)
                    {
                        msg = (dados.detalhes as Array).join("\n");
                    }
                    falha(msg);
                    return;
                }
                ok(dados);
            });

            servico.addEventListener(FaultEvent.FAULT, function(e:FaultEvent):void
            {
                falha("Falha de comunicação com " + url + "\n" + e.fault.faultString
                    + (e.fault.faultDetail ? "\n" + e.fault.faultDetail : ""));
            });

            if (corpo != null)
            {
                servico.send(JSON.stringify(corpo));
            }
            else
            {
                servico.send();
            }
        }
    }
}
