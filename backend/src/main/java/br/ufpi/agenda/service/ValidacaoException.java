package br.ufpi.agenda.service;

import java.util.List;

/** Erro de validação de dados enviados pelo cliente (vira HTTP 400). */
public class ValidacaoException extends Exception {

    private static final long serialVersionUID = 1L;

    private final List<String> erros;

    public ValidacaoException(List<String> erros) {
        super(juntar(erros));
        this.erros = erros;
    }

    public List<String> getErros() {
        return erros;
    }

    private static String juntar(List<String> erros) {
        // String.join só existe no Java 8, então juntamos manualmente
        StringBuilder sb = new StringBuilder();
        for (String e : erros) {
            if (sb.length() > 0) {
                sb.append("; ");
            }
            sb.append(e);
        }
        return sb.toString();
    }
}
