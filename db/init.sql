-- Esquema da Agenda de Contatos (MySQL 5.7)
-- Executado automaticamente pelo container MySQL na primeira inicialização
-- (arquivos em /docker-entrypoint-initdb.d).

SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS contato (
    id      BIGINT       NOT NULL AUTO_INCREMENT,
    nome    VARCHAR(120) NOT NULL,
    rua     VARCHAR(200) NULL,
    cep     VARCHAR(20)  NULL,
    cidade  VARCHAR(100) NULL,
    estado  VARCHAR(60)  NULL,
    pais    VARCHAR(60)  NULL,
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_contato_nome (nome)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contato_telefone (
    id         BIGINT      NOT NULL AUTO_INCREMENT,
    contato_id BIGINT      NOT NULL,
    numero     VARCHAR(30) NOT NULL,
    ordem      INT         NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_tel_contato (contato_id),
    CONSTRAINT fk_tel_contato FOREIGN KEY (contato_id) REFERENCES contato (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS contato_email (
    id         BIGINT       NOT NULL AUTO_INCREMENT,
    contato_id BIGINT       NOT NULL,
    email      VARCHAR(150) NOT NULL,
    ordem      INT          NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    KEY idx_email_contato (contato_id),
    CONSTRAINT fk_email_contato FOREIGN KEY (contato_id) REFERENCES contato (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dados de exemplo
INSERT INTO contato (id, nome, rua, cep, cidade, estado, pais) VALUES
 (1, 'Ana Beatriz Sousa',  'Av. Universitária, 1310', '64049-550', 'Teresina',       'PI', 'Brasil'),
 (2, 'Carlos Eduardo Lima', 'Rua das Flores, 45',     '60115-000', 'Fortaleza',      'CE', 'Brasil'),
 (3, 'María Fernández',     'Calle 50, Edificio Sol', '0801',      'Ciudad de Panamá', 'Panamá', 'Panamá');

INSERT INTO contato_telefone (contato_id, numero, ordem) VALUES
 (1, '(86) 3215-5500', 0), (1, '(86) 99999-1234', 1),
 (2, '(85) 98888-4321', 0),
 (3, '+507 6000-1111', 0);

INSERT INTO contato_email (contato_id, email, ordem) VALUES
 (1, 'ana.sousa@exemplo.com.br', 0), (1, 'ana@ufpi.edu.br', 1),
 (2, 'carlos.lima@exemplo.com.br', 0),
 (3, 'maria.fernandez@ejemplo.com.pa', 0);
