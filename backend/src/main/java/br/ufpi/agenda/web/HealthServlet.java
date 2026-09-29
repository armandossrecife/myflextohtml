package br.ufpi.agenda.web;

import br.ufpi.agenda.dao.ConnectionFactory;

import javax.servlet.annotation.WebServlet;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.sql.Connection;
import java.util.LinkedHashMap;
import java.util.Map;

/** GET /api/health: informa versão do Java e se o banco responde. */
@WebServlet(name = "health", urlPatterns = {"/api/health"})
public class HealthServlet extends ApiServlet {

    private static final long serialVersionUID = 1L;

    @Override
    protected void doGet(HttpServletRequest req, HttpServletResponse resp) throws IOException {
        Map<String, Object> info = new LinkedHashMap<>();
        info.put("java", System.getProperty("java.version"));
        info.put("servidor", getServletContext().getServerInfo());
        int status = 200;
        try (Connection con = ConnectionFactory.getConnection()) {
            info.put("banco", con.getMetaData().getDatabaseProductName() + " "
                    + con.getMetaData().getDatabaseProductVersion());
            info.put("status", "UP");
        } catch (Exception e) {
            info.put("status", "DOWN");
            info.put("erro", e.getMessage());
            status = 503;
        }
        json(req, resp, status, info);
    }
}
