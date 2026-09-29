package br.ufpi.agenda
{
    import org.apache.royale.events.Event;
    import org.apache.royale.net.HTTPConstants;
    import org.apache.royale.net.HTTPService;

    /**
     * Cliente da API REST de contatos (versão Apache Royale / HTML5).
     * Mantém o mesmo contrato de URL usado pelo cliente Flex original:
     * ?suppress_response_codes=true e POST + _method=PUT|DELETE.
     */
    public class ApiClient
    {
        private var baseUrl:String;

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
                + "?suppress_response_codes=true&_ts=" + new Date().getTime() + extra;

            var servico:HTTPService = new HTTPService();
            if (metodo == "GET")
            {
                servico.method = HTTPConstants.GET;
            }
            else
            {
                servico.method = HTTPConstants.POST;
                servico.contentType = "application/json";
                if (metodo != "POST")
                {
                    url += "&_method=" + metodo;
                }
                servico.contentData = JSON.stringify(corpo);
            }
            servico.url = url;

            servico.addEventListener(HTTPConstants.COMPLETE, function(e:Event):void
            {
                var texto:String = servico.data;
                if (servico.status != 200)
                {
                    falha("HTTP " + servico.status + " em " + url);
                    return;
                }
                var dados:Object = null;
                try
                {
                    dados = (texto != null && texto.length > 0) ? JSON.parse(texto) : null;
                }
                catch (erro:Error)
                {
                    falha("Resposta inválida do servidor: " + String(texto).substr(0, 200));
                    return;
                }
                if (dados != null && !(dados is Array) && dados.hasOwnProperty("erro"))
                {
                    var msg:String = String(dados["erro"]);
                    if (dados.hasOwnProperty("detalhes") && dados["detalhes"] is Array)
                    {
                        msg = (dados["detalhes"] as Array).join("\n");
                    }
                    falha(msg);
                    return;
                }
                ok(dados);
            });
            servico.addEventListener(HTTPConstants.IO_ERROR, function(e:Event):void
            {
                falha("Falha de comunicação com " + url);
            });
            servico.send();
        }
    }
}
