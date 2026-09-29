package br.ufpi.agenda.model;

import java.io.Serializable;

/** Endereço de um contato (armazenado nas colunas da própria tabela contato). */
public class Endereco implements Serializable {

    private static final long serialVersionUID = 1L;

    private String rua;
    private String cep;
    private String cidade;
    private String estado;
    private String pais;

    public Endereco() {
    }

    public Endereco(String rua, String cep, String cidade, String estado, String pais) {
        this.rua = rua;
        this.cep = cep;
        this.cidade = cidade;
        this.estado = estado;
        this.pais = pais;
    }

    public String getRua() { return rua; }
    public void setRua(String rua) { this.rua = rua; }

    public String getCep() { return cep; }
    public void setCep(String cep) { this.cep = cep; }

    public String getCidade() { return cidade; }
    public void setCidade(String cidade) { this.cidade = cidade; }

    public String getEstado() { return estado; }
    public void setEstado(String estado) { this.estado = estado; }

    public String getPais() { return pais; }
    public void setPais(String pais) { this.pais = pais; }
}
