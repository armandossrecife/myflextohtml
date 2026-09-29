package br.ufpi.agenda.dao;

import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.SQLException;

/**
 * Fábrica de conexões JDBC. Os parâmetros vêm de variáveis de ambiente
 * (definidas no docker-compose.yml), com valores padrão para o ambiente Docker.
 */
public final class ConnectionFactory {

    private static final String URL = env("DB_URL",
            "jdbc:mysql://db:3306/agenda?useUnicode=true&characterEncoding=UTF-8&useSSL=false");
    private static final String USER = env("DB_USER", "agenda");
    private static final String PASSWORD = env("DB_PASSWORD", "agenda");

    static {
        try {
            Class.forName("com.mysql.jdbc.Driver");
        } catch (ClassNotFoundException e) {
            throw new IllegalStateException("Driver MySQL não encontrado no classpath", e);
        }
    }

    private ConnectionFactory() {
    }

    public static Connection getConnection() throws SQLException {
        return DriverManager.getConnection(URL, USER, PASSWORD);
    }

    private static String env(String nome, String padrao) {
        String valor = System.getenv(nome);
        return (valor == null || valor.trim().isEmpty()) ? padrao : valor.trim();
    }
}
