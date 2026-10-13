/**
 * API do Buscador de Scripts (Google Apps Script)
 * Permite listar, adicionar, editar e excluir linhas da planilha.
 *
 * ANTES DE PUBLICAR: troque a SENHA abaixo por uma senha forte.
 */
const ID_PLANILHA = "13bnnwDdEty5VoVOMDRDXm5U8GoKaNJo6IjJoBiZVTVw";
const GID = 0;                       // gid da aba (o número depois de "gid=" no link)
const SENHA = "TROQUE-ESTA-SENHA";   // a mesma senha será digitada na página admin.html

/**
 * Rode esta função UMA VEZ no editor (menu "Executar") para conceder as permissões
 * de acesso à planilha. Sem isso, a página admin.html dá "Failed to fetch".
 */
function autorizar() {
  const nome = SpreadsheetApp.openById(ID_PLANILHA).getName();
  LockService.getScriptLock();
  Logger.log("Autorizado. Planilha: " + nome);
}

function doGet() {
  return resposta({ ok: true, mensagem: "API ativa." });
}

function doPost(e) {
  let saida;
  try {
    const req = JSON.parse(e.postData.contents);
    if (req.senha !== SENHA) throw new Error("Senha incorreta.");

    const trava = LockService.getScriptLock();
    trava.waitLock(20000); // evita duas edições simultâneas
    try {
      saida = executar(req);
    } finally {
      trava.releaseLock();
    }
  } catch (erro) {
    saida = { ok: false, erro: String(erro.message || erro) };
  }
  return resposta(saida);
}

function resposta(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function executar(req) {
  const aba = SpreadsheetApp.openById(ID_PLANILHA)
    .getSheets().find((s) => s.getSheetId() === GID);
  if (!aba) throw new Error("Aba não encontrada (confira o GID).");

  const cabecalho = aba.getRange(1, 1, 1, aba.getLastColumn()).getValues()[0]
    .map((v) => String(v).trim().toLowerCase());
  const colA = cabecalho.indexOf("assunto") + 1;
  const colS = cabecalho.indexOf("script") + 1;
  if (!colA || !colS) throw new Error("A primeira linha deve ter as colunas 'Assunto' e 'Script'.");

  const lerLinha = (n) => ({
    assunto: String(aba.getRange(n, colA).getValue()).trim(),
    script: String(aba.getRange(n, colS).getValue()).trim(),
  });

  // Garante que a linha ainda é a mesma que a pessoa estava vendo.
  const conferir = (n, original) => {
    if (!n || n < 2 || n > aba.getLastRow()) throw new Error("Linha não existe mais. Atualize a lista.");
    const atual = lerLinha(n);
    if (!original || atual.assunto !== original.assunto || atual.script !== original.script) {
      throw new Error("Esta linha foi alterada por outra pessoa. Atualize a lista.");
    }
  };

  const gravar = (n, dados) => {
    const a = aba.getRange(n, colA), s = aba.getRange(n, colS);
    a.setNumberFormat("@").setValue(dados.assunto); // "@" = texto puro (sem fórmulas)
    s.setNumberFormat("@").setValue(dados.script);
  };

  const validar = (d) => {
    if (!d || !String(d.assunto || "").trim() || !String(d.script || "").trim()) {
      throw new Error("Preencha o assunto e o script.");
    }
    return { assunto: String(d.assunto).trim(), script: String(d.script).trim() };
  };

  switch (req.acao) {
    case "listar": {
      const valores = aba.getDataRange().getValues();
      const itens = [];
      for (let i = 1; i < valores.length; i++) {
        const assunto = String(valores[i][colA - 1]).trim();
        const script = String(valores[i][colS - 1]).trim();
        if (assunto || script) itens.push({ linha: i + 1, assunto, script });
      }
      return { ok: true, itens };
    }
    case "adicionar": {
      const dados = validar(req.dados);
      const nova = Math.max(aba.getLastRow(), 1) + 1;
      gravar(nova, dados);
      return { ok: true };
    }
    case "editar": {
      const dados = validar(req.dados);
      conferir(req.linha, req.original);
      gravar(req.linha, dados);
      return { ok: true };
    }
    case "excluir": {
      conferir(req.linha, req.original);
      aba.deleteRow(req.linha);
      return { ok: true };
    }
    default:
      throw new Error("Ação desconhecida.");
  }
}
