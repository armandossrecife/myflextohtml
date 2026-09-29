package br.ufpi.agenda.web;

import br.ufpi.agenda.model.Contato;
import br.ufpi.agenda.service.ContatoService;
import br.ufpi.agenda.service.ValidacaoException;
import com.google.gson.JsonSyntaxException;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.sql.SQLException;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.logging.Level;
import java.util.logging.Logger;

/**
 * API REST de contatos.
 *
 * <pre>
 * GET    /api/contatos            lista (parâmetro opcional q = filtro)
 * GET    /api/contatos/{id}       busca por id
 * POST   /api/contatos            cria
 * PUT    /api/contatos/{id}       atualiza   (ou POST ?_method=PUT)
 * DELETE /api/contatos/{id}       exclui     (ou POST ?_method=DELETE)
 * </pre>
 */
@WebServlet(name = "contatos", urlPatterns = {"/api/contatos", "/api/contatos/*"})
public class ContatoServlet extends ApiServlet {

    private static final long serialVersionUID = 1L;
    private static final Logger LOG = Logger.getLogger(ContatoServlet.class.getName());

    private final transient ContatoService service = new ContatoService();

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        try {
            Long id = idDaUrl(req);
            if (id == null) {
                json(req, resp, 200, service.listar(parametroDaQueryString(req, "q")));
                return;
            }
            Contato c = service.buscar(id);
            if (c == null) {
                erro(req, resp, 404, "Contato " + id + " não encontrado");
            } else {
                json(req, resp, 200, c);
            }
        } catch (IllegalArgumentException e) {
            erro(req, resp, 400, e.getMessage());
        } catch (SQLException e) {
            falhaBanco(req, resp, e);
        }
    }

    @Override
    protected void doPost(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        try {
            if (idDaUrl(req) != null) {
                erro(req, resp, 405, "Use PUT (ou POST ?_method=PUT) para atualizar um contato");
                return;
            }
            Contato criado = service.criar(lerContato(req));
            resp.setHeader("Location", req.getContextPath() + "/api/contatos/" + criado.getId());
            json(req, resp, 201, criado);
        } catch (ValidacaoException e) {
            erro(req, resp, 400, e.getMessage(), e.getErros());
        } catch (IllegalArgumentException e) {
            erro(req, resp, 400, e.getMessage());
        } catch (SQLException e) {
            falhaBanco(req, resp, e);
        }
    }

    @Override
    protected void doPut(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        try {
            Long id = idDaUrl(req);
            if (id == null) {
                erro(req, resp, 400, "Informe o id na URL: /api/contatos/{id}");
                return;
            }
            Contato atualizado = service.atualizar(id, lerContato(req));
            if (atualizado == null) {
                erro(req, resp, 404, "Contato " + id + " não encontrado");
            } else {
                json(req, resp, 200, atualizado);
            }
        } catch (ValidacaoException e) {
            erro(req, resp, 400, e.getMessage(), e.getErros());
        } catch (IllegalArgumentException e) {
            erro(req, resp, 400, e.getMessage());
        } catch (SQLException e) {
            falhaBanco(req, resp, e);
        }
    }

    @Override
    protected void doDelete(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        try {
            Long id = idDaUrl(req);
            if (id == null) {
                erro(req, resp, 400, "Informe o id na URL: /api/contatos/{id}");
                return;
            }
            if (!service.excluir(id)) {
                erro(req, resp, 404, "Contato " + id + " não encontrado");
                return;
            }
            Map<String, Object> ok = new LinkedHashMap<>();
            ok.put("excluido", id);
            json(req, resp, 200, ok);
        } catch (IllegalArgumentException e) {
            erro(req, resp, 400, e.getMessage());
        } catch (SQLException e) {
            falhaBanco(req, resp, e);
        }
    }

    // ------------------------------------------------------------------ auxiliares

    /** Extrai o {id} de /api/contatos/{id}; devolve null para /api/contatos. */
    private static Long idDaUrl(HttpServletRequest req) {
        String info = req.getPathInfo();
        if (info == null || "/".equals(info)) {
            return null;
        }
        String bruto = info.substring(1);
        if (bruto.endsWith("/")) {
            bruto = bruto.substring(0, bruto.length() - 1);
        }
        try {
            return Long.valueOf(bruto);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException("Id inválido: " + bruto);
        }
    }

    private static Contato lerContato(HttpServletRequest req) throws IOException {
        String corpo = lerCorpo(req);
        if (corpo.trim().isEmpty()) {
            throw new IllegalArgumentException("Corpo JSON obrigatório");
        }
        try {
            return GSON.fromJson(corpo, Contato.class);
        } catch (JsonSyntaxException e) {
            throw new IllegalArgumentException("JSON inválido: " + e.getMessage());
        }
    }

    private static void falhaBanco(HttpServletRequest req, HttpServletResponse resp, SQLException e)
            throws IOException {
        LOG.log(Level.SEVERE, "Erro de banco de dados", e);
        erro(req, resp, 500, "Erro no banco de dados: " + e.getMessage());
    }
}
