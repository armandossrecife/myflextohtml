package br.ufpi.agenda.service;

import br.ufpi.agenda.dao.ContatoDao;
import br.ufpi.agenda.model.Contato;

import java.sql.SQLException;
import java.util.List;

/** Regras de negócio da agenda: valida e delega a persistência ao DAO. */
public class ContatoService {

    private final ContatoDao dao;
    private final ContatoValidator validator;

    public ContatoService() {
        this(new ContatoDao(), new ContatoValidator());
    }

    public ContatoService(ContatoDao dao, ContatoValidator validator) {
        this.dao = dao;
        this.validator = validator;
    }

    public List<Contato> listar(String filtro) throws SQLException {
        return dao.listar(filtro);
    }

    public Contato buscar(long id) throws SQLException {
        return dao.buscarPorId(id);
    }

    public Contato criar(Contato c) throws SQLException, ValidacaoException {
        validator.normalizarEValidar(c);
        c.setId(null);
        return dao.inserir(c);
    }

    /** @return o contato atualizado, ou {@code null} se o id não existir */
    public Contato atualizar(long id, Contato c) throws SQLException, ValidacaoException {
        validator.normalizarEValidar(c);
        c.setId(id);
        return dao.atualizar(c) ? dao.buscarPorId(id) : null;
    }

    public boolean excluir(long id) throws SQLException {
        return dao.excluir(id);
    }
}
