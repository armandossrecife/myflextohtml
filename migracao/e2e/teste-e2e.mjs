// Teste E2E (navegador real, Chromium headless) da aplicação HTML5 migrada.
// Uso: node teste-e2e.mjs <url-da-aplicacao> <pasta-de-saida>
// Exercita a tela como um usuário: lista, seleção, criação, exclusão, e confere o resultado na API Java 7.
import { chromium } from "playwright";
import fs from "node:fs";
import path from "node:path";

const url = (process.argv[2] || "http://localhost:8082/").replace(/\/?$/, "/");
const saida = process.argv[3] || "./resultado-e2e";
fs.mkdirSync(saida, { recursive: true });

const passos = [];
const errosJs = [];
const log = (nivel, msg) => {
  const linha = `${new Date().toISOString()} [${nivel}] ${msg}`;
  console.log(linha);
  fs.appendFileSync(path.join(saida, "e2e.log"), linha + "\n");
};
const api = async (caminho, opcoes) => {
  const r = await fetch(url + "api" + caminho, opcoes);
  return r.json();
};
async function passo(nome, fn) {
  const t0 = Date.now();
  try {
    const detalhe = await fn();
    passos.push({ nome, ok: true, detalhe: detalhe || "", ms: Date.now() - t0 });
    log("OK", `${nome}${detalhe ? " - " + detalhe : ""}`);
    return true;
  } catch (e) {
    passos.push({ nome, ok: false, detalhe: String(e.message || e).slice(0, 400), ms: Date.now() - t0 });
    log("ERRO", `${nome} - ${String(e.message || e).slice(0, 400)}`);
    return false;
  }
}
async function esperar(condicao, ms = 10000) {
  const fim = Date.now() + ms;
  while (Date.now() < fim) {
    if (await condicao()) return true;
    await new Promise((r) => setTimeout(r, 300));
  }
  return false;
}
function campo(page, rotulo) {
  // campos Jewel ficam dentro de .jewel.formitem com o rótulo; alternativa: acessibilidade/placeholder
  return page.locator(`.jewel.formitem:has-text("${rotulo}") input`).first()
    .or(page.getByLabel(new RegExp(rotulo, "i")).first());
}
const botao = (page, nome) => page.getByRole("button", { name: new RegExp(`^\\s*${nome}\\s*$`, "i") }).first();

const navegador = await chromium.launch();
const page = await navegador.newPage({ viewport: { width: 1440, height: 950 } });
page.on("pageerror", (e) => { errosJs.push(e.message); log("ERRO", "JS: " + e.message); });

const nomeTeste = "E2E Royale " + Date.now();
let contatos = [];

await passo("API Java 7 acessível pela aplicação (/api/health)", async () => {
  const h = await api("/health");
  if (h.status !== "UP") throw new Error(JSON.stringify(h));
  contatos = await api("/contatos");
  return `java ${h.java}, ${contatos.length} contato(s)`;
});

await passo("Página HTML5 carrega sem Flash/Ruffle", async () => {
  const resp = await page.goto(url, { waitUntil: "load" });
  if (!resp.ok()) throw new Error("HTTP " + resp.status());
  const html = await page.content();
  if (/ruffle|shockwave|\.swf/i.test(html)) throw new Error("a página ainda depende de SWF/Ruffle");
  return "HTTP " + resp.status();
});

await passo("Grade lista os contatos vindos da API", async () => {
  if (!contatos.length) return "API sem contatos (nada a conferir)";
  await page.getByText(contatos[0].nome, { exact: true }).first().waitFor({ timeout: 15000 });
  await page.screenshot({ path: path.join(saida, "01-lista.png") });
  return `"${contatos[0].nome}" visível`;
});

await passo("Selecionar contato preenche o formulário", async () => {
  if (!contatos.length) return "sem contatos";
  await page.getByText(contatos[0].nome, { exact: true }).first().click();
  const ok = await esperar(async () => (await campo(page, "Nome").inputValue()) === contatos[0].nome);
  if (!ok) throw new Error("campo Nome não recebeu o contato selecionado");
  await page.screenshot({ path: path.join(saida, "02-selecao.png") });
  return "campo Nome = " + contatos[0].nome;
});

await passo("Todos os campos do formulário estão visíveis (nenhum cortado)", async () => {
  // um campo é "cortado" quando fica fora de um container com overflow hidden/clip (não dá para rolar
  // até ele). Ex.: j:Card com height fixo envolvendo o j:Form.
  const cortados = await page.evaluate(() => {
    const problemas = [];
    const campos = [...document.querySelectorAll("input, textarea, select")]
      .filter((el) => el.type !== "hidden" && getComputedStyle(el).display !== "none");
    for (const el of campos) {
      const rotulo = (el.closest(".jewel.formitem")?.innerText || el.placeholder || el.name || "campo")
        .split("\n")[0].trim();
      const r = el.getBoundingClientRect();
      if (r.width < 2 || r.height < 2) { problemas.push(`${rotulo} (tamanho zero)`); continue; }
      for (let pai = el.parentElement; pai && pai !== document.body; pai = pai.parentElement) {
        const estilo = getComputedStyle(pai);
        if (!["hidden", "clip"].includes(estilo.overflowY) && !["hidden", "clip"].includes(estilo.overflowX)) continue;
        const rp = pai.getBoundingClientRect();
        if (r.bottom > rp.bottom + 1 || r.top < rp.top - 1 || r.right > rp.right + 1 || r.left < rp.left - 1) {
          problemas.push(`${rotulo} (cortado por ${pai.className.split(" ").slice(0, 2).join(".") || pai.tagName})`);
          break;
        }
      }
    }
    return problemas;
  });
  if (cortados.length) {
    await page.screenshot({ path: path.join(saida, "erro-campos-cortados.png"), fullPage: true });
    throw new Error("campos fora da área visível: " + cortados.join(", "));
  }
  const total = await page.locator("input, textarea, select").count();
  return `${total} campo(s) conferido(s)`;
});

await passo("Criar contato pela tela (Novo contato + Salvar)", async () => {
  await botao(page, "Novo contato").click();
  await campo(page, "Nome").fill(nomeTeste);
  await botao(page, "Salvar").click();
  const ok = await esperar(async () => (await api("/contatos?q=" + encodeURIComponent(nomeTeste))).length === 1);
  if (!ok) throw new Error("contato não apareceu na API");
  await page.getByText(nomeTeste, { exact: true }).first().waitFor({ timeout: 10000 });
  await page.screenshot({ path: path.join(saida, "03-criado.png") });
  return "gravado no MySQL via API Java 7";
});

await passo("Excluir contato pela tela (Excluir + confirmação)", async () => {
  await page.getByText(nomeTeste, { exact: true }).first().click();
  await botao(page, "Excluir").click();
  const confirmar = page.getByRole("button", { name: /^\s*(sim|yes|ok)\s*$/i }).first();
  await confirmar.waitFor({ timeout: 5000 });
  await page.screenshot({ path: path.join(saida, "04-confirmacao.png") });
  await confirmar.click();
  const ok = await esperar(async () => (await api("/contatos?q=" + encodeURIComponent(nomeTeste))).length === 0);
  if (!ok) throw new Error("contato continua na API");
  return "removido da API";
});

await passo("Nenhum erro de JavaScript", async () => {
  if (errosJs.length) throw new Error(errosJs.join(" | "));
  return "0 erros";
});

await page.screenshot({ path: path.join(saida, "05-final.png") });
await navegador.close();

// limpeza, caso algum passo tenha falhado no meio
try {
  for (const c of await api("/contatos?q=" + encodeURIComponent("E2E Royale "))) {
    await api(`/contatos/${c.id}?_method=DELETE`, { method: "POST", body: "{}", headers: { "Content-Type": "application/json" } });
  }
} catch (e) {
  log("AVISO", "limpeza dos contatos de teste falhou: " + e.message);
}

const resultado = { url, sucesso: passos.every((p) => p.ok), passos, errosJs };
fs.writeFileSync(path.join(saida, "resultado-e2e.json"), JSON.stringify(resultado, null, 2));
log(resultado.sucesso ? "OK" : "ERRO", `E2E ${resultado.sucesso ? "APROVADO" : "REPROVADO"}: ` +
  `${passos.filter((p) => p.ok).length}/${passos.length} passos`);
process.exit(resultado.sucesso ? 0 : 1);
