package br.ufpi.agenda.model;

import java.io.Serializable;
import java.util.ArrayList;
import java.util.List;

/** Contato da agenda: id, nome, telefones, e-mails e endereço. */
public class Contato implements Serializable {

    private static final long serialVersionUID = 1L;

    private Long id;
    private String nome;
    private List<String> telefones = new ArrayList<>();
    private List<String> emails = new ArrayList<>();
    private Endereco endereco = new Endereco();

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }

    public String getNome() { return nome; }
    public void setNome(String nome) { this.nome = nome; }

    public List<String> getTelefones() { return telefones; }
    public void setTelefones(List<String> telefones) {
        this.telefones = telefones != null ? telefones : new ArrayList<String>();
    }

    public List<String> getEmails() { return emails; }
    public void setEmails(List<String> emails) {
        this.emails = emails != null ? emails : new ArrayList<String>();
    }

    public Endereco getEndereco() { return endereco; }
    public void setEndereco(Endereco endereco) {
        this.endereco = endereco != null ? endereco : new Endereco();
    }
}
