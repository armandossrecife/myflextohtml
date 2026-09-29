package br.ufpi.agenda.service;

import br.ufpi.agenda.model.Contato;
import br.ufpi.agenda.model.Endereco;

import java.util.ArrayList;
import java.util.List;
import java.util.regex.Pattern;

/**
 * Normaliza (trim, remove itens vazios/duplicados) e valida um contato.
 * Não depende de banco de dados, por isso é fácil de testar.
 */
public class ContatoValidator {

    private static final Pattern EMAIL = Pattern.compile("^[^@\\s]+@[^@\\s]+\\.[^@\\s]+$");
    private static final Pattern TELEFONE = Pattern.compile("^[0-9+()\\-.\\s]{6,30}$");

    public static final int MAX_NOME = 120;
    public static final int MAX_RUA = 200;
    public static final int MAX_CEP = 20;
    public static final int MAX_CIDADE = 100;
    public static final int MAX_ESTADO = 60;
    public static final int MAX_PAIS = 60;
    public static final int MAX_EMAIL = 150;

    public void normalizarEValidar(Contato c) throws ValidacaoException {
        List<String> erros = new ArrayList<>();
        if (c == null) {
            erros.add("Corpo da requisição vazio ou inválido");
            throw new ValidacaoException(erros);
        }

        c.setNome(limpar(c.getNome()));
        c.setTelefones(limparLista(c.getTelefones()));
        c.setEmails(limparLista(c.getEmails()));

        Endereco e = c.getEndereco() != null ? c.getEndereco() : new Endereco();
        e.setRua(limpar(e.getRua()));
        e.setCep(limpar(e.getCep()));
        e.setCidade(limpar(e.getCidade()));
        e.setEstado(limpar(e.getEstado()));
        e.setPais(limpar(e.getPais()));
        c.setEndereco(e);

        if (c.getNome() == null) {
            erros.add("O nome é obrigatório");
        } else if (c.getNome().length() > MAX_NOME) {
            erros.add("O nome deve ter no máximo " + MAX_NOME + " caracteres");
        }

        for (String tel : c.getTelefones()) {
            if (!TELEFONE.matcher(tel).matches()) {
                erros.add("Telefone inválido: " + tel);
            }
        }
        for (String email : c.getEmails()) {
            if (email.length() > MAX_EMAIL || !EMAIL.matcher(email).matches()) {
                erros.add("E-mail inválido: " + email);
            }
        }

        tamanho(erros, "rua", e.getRua(), MAX_RUA);
        tamanho(erros, "CEP", e.getCep(), MAX_CEP);
        tamanho(erros, "cidade", e.getCidade(), MAX_CIDADE);
        tamanho(erros, "estado", e.getEstado(), MAX_ESTADO);
        tamanho(erros, "país", e.getPais(), MAX_PAIS);

        if (!erros.isEmpty()) {
            throw new ValidacaoException(erros);
        }
    }

    private static void tamanho(List<String> erros, String campo, String valor, int max) {
        if (valor != null && valor.length() > max) {
            erros.add("O campo " + campo + " deve ter no máximo " + max + " caracteres");
        }
    }

    private static String limpar(String s) {
        if (s == null) {
            return null;
        }
        String t = s.trim();
        return t.isEmpty() ? null : t;
    }

    private static List<String> limparLista(List<String> itens) {
        List<String> resultado = new ArrayList<>();
        if (itens == null) {
            return resultado;
        }
        for (String item : itens) {
            String t = limpar(item);
            if (t != null && !resultado.contains(t)) {
                resultado.add(t);
            }
        }
        return resultado;
    }
}
