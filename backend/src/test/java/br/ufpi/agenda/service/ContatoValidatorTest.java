package br.ufpi.agenda.service;

import br.ufpi.agenda.model.Contato;
import org.junit.Test;

import java.util.Arrays;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

public class ContatoValidatorTest {

    private final ContatoValidator validator = new ContatoValidator();

    @Test
    public void normalizaEspacosListasVaziasEDuplicadas() throws Exception {
        Contato c = new Contato();
        c.setNome("  Ana Souza  ");
        c.setTelefones(Arrays.asList(" (86) 99999-0000 ", "", "(86) 99999-0000", null));
        c.setEmails(Arrays.asList("ana@ufpi.edu.br", "   "));
        c.getEndereco().setCidade("  Teresina ");
        c.getEndereco().setRua("   ");

        validator.normalizarEValidar(c);

        assertEquals("Ana Souza", c.getNome());
        assertEquals(Arrays.asList("(86) 99999-0000"), c.getTelefones());
        assertEquals(Arrays.asList("ana@ufpi.edu.br"), c.getEmails());
        assertEquals("Teresina", c.getEndereco().getCidade());
        assertNull(c.getEndereco().getRua());
    }

    @Test
    public void rejeitaNomeVazioEEmailInvalido() {
        Contato c = new Contato();
        c.setNome("   ");
        c.setEmails(Arrays.asList("sem-arroba"));
        try {
            validator.normalizarEValidar(c);
            fail("Deveria lançar ValidacaoException");
        } catch (ValidacaoException e) {
            assertEquals(2, e.getErros().size());
            assertTrue(e.getMessage().contains("nome"));
            assertTrue(e.getMessage().contains("sem-arroba"));
        }
    }

    @Test
    public void aceitaListasNulasEEnderecoNulo() throws Exception {
        Contato c = new Contato();
        c.setNome("Bob");
        c.setTelefones(null);
        c.setEmails(null);
        c.setEndereco(null);

        validator.normalizarEValidar(c);

        assertTrue(c.getTelefones().isEmpty());
        assertTrue(c.getEmails().isEmpty());
        assertNull(c.getEndereco().getPais());
    }

    @Test(expected = ValidacaoException.class)
    public void rejeitaTelefoneComLetras() throws Exception {
        Contato c = new Contato();
        c.setNome("Carla");
        c.setTelefones(Arrays.asList("ligar depois"));
        validator.normalizarEValidar(c);
    }
}
