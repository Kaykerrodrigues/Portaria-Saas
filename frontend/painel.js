const LIMIT = 20;
let offsetAtual = 0, totalPessoas = 0;
let dadosEntradaPendente = null, dadosSaidaPendente = null;
let fotoCadTemp = null, fotoEditTemp = null, fotoEditRemover = false;
let dadosRelatorio = [], dadosRelatorioVeic = [], qrTokenAtual = null;
let buscaTimer = null, buscaMovTimer = {};

window.addEventListener("DOMContentLoaded", () => {
    if (!exigirLogin(["sindico","admin","porteiro"])) return;
    const s = getSessao();
    document.getElementById("usuario-logado").textContent = `👤 ${s.usuario} (${s.perfil})`;
    document.getElementById("topo-nome").textContent = `🏢 ${s.condominio_nome || "Portaria Pro"}`;
    document.getElementById("dash-titulo").textContent = s.condominio_nome || "Dashboard";
    const isAdmin = ["sindico","admin"].includes(s.perfil);
    const isSindico = s.perfil === "sindico";
    document.querySelectorAll(".aba-admin-only").forEach(el => el.style.display = isAdmin ? "" : "none");
    document.querySelectorAll(".aba-sindico-only").forEach(el => el.style.display = isSindico ? "" : "none");
    carregarDashboard();
});

// ===== ABAS =====
function mostrarAba(nome, btn) {
    document.querySelectorAll(".aba-conteudo").forEach(el => el.style.display = "none");
    document.querySelectorAll(".aba").forEach(el => el.classList.remove("ativa"));
    document.getElementById(`aba-${nome}`).style.display = "block";
    btn.classList.add("ativa");
    if (nome === "dashboard")    carregarDashboard();
    if (nome === "pessoas")      { offsetAtual = 0; carregarPessoas(); }
    if (nome === "dentro")       carregarDentro();
    if (nome === "veiculos")     carregarVeiculos();
    if (nome === "qrcode")       carregarQRCodes();
    if (nome === "equipe")       carregarEquipe();
    if (nome === "configuracoes") carregarConfiguracoes();
}

function mostrarVeiculosTab(nome, btn) {
    ["lista","dentro","movimento","relatorio"].forEach(n => document.getElementById(`veic-${n}`).style.display = "none");
    document.querySelectorAll(".admin-tab").forEach(b => { if(b.closest("#aba-veiculos")) b.classList.remove("ativa"); });
    document.getElementById(`veic-${nome}`).style.display = "block";
    btn.classList.add("ativa");
    if (nome === "lista")   carregarVeiculos();
    if (nome === "dentro")  carregarVeiculosDentro();
}

function mostrarQRTab(nome, btn) {
    ["gerar","validar","lista"].forEach(n => document.getElementById(`qr-${n}`).style.display = "none");
    document.querySelectorAll(".admin-tab").forEach(b => { if(b.closest("#aba-qrcode")) b.classList.remove("ativa"); });
    document.getElementById(`qr-${nome}`).style.display = "block";
    btn.classList.add("ativa");
    if (nome === "lista") carregarQRCodes();
}

function mostrarConfigTab(nome, btn) {
    ["dados","senha","backup","log"].forEach(n => document.getElementById(`conf-${n}`).style.display = "none");
    document.querySelectorAll(".admin-tab").forEach(b => { if(b.closest("#aba-configuracoes")) b.classList.remove("ativa"); });
    document.getElementById(`conf-${nome}`).style.display = "block";
    btn.classList.add("ativa");
    if (nome === "backup") carregarBackups();
    if (nome === "log")    carregarLog();
}

// ===== DASHBOARD =====
async function carregarDashboard() {
    const res = await fetch(`${API}/dashboard`, { headers: authHeaders() });
    if (!res.ok) return;
    const d = await res.json();
    document.getElementById("stat-total").textContent    = d.total_pessoas;
    document.getElementById("stat-dentro").textContent   = d.dentro_agora;
    document.getElementById("stat-veiculos").textContent = d.veiculos_dentro;
    document.getElementById("stat-entradas").textContent = d.entradas_hoje;
    const tbody = document.getElementById("tabela-ultimas");
    tbody.innerHTML = "";
    if (!d.ultimas_movimentacoes.length) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#999">Sem movimentações.</td></tr>`; return; }
    d.ultimas_movimentacoes.forEach(e => {
        const badge = e.acao === "entrada" ? `<span class="badge badge-entrada">ENTRADA</span>` : `<span class="badge badge-saida">SAÍDA</span>`;
        tbody.innerHTML += `<tr><td>${e.data_hora.replace("T"," ")}</td><td>${badge}</td><td>${e.nome}</td><td>${e.tipo}</td><td>${e.porteiro}</td></tr>`;
    });
}

// ===== PESSOAS =====
async function carregarPessoas() {
    const tipo = document.getElementById("filtro-tipo").value;
    const url = tipo ? `${API}/pessoas/tipo/${tipo}` : `${API}/pessoas?limit=${LIMIT}&offset=${offsetAtual}`;
    const res = await fetch(url, { headers: authHeaders() });
    if (!res.ok) return;
    const data = await res.json();
    if (tipo) { renderizarPessoas(data); document.getElementById("paginacao-pessoas").innerHTML = ""; }
    else { totalPessoas = data.total; renderizarPessoas(data.data); renderizarPaginacao(); }
}

function buscarPorNome() {
    clearTimeout(buscaTimer);
    buscaTimer = setTimeout(async () => {
        const nome = document.getElementById("busca-nome").value.trim();
        if (!nome) { offsetAtual = 0; carregarPessoas(); return; }
        const res = await fetch(`${API}/pessoas/busca?nome=${encodeURIComponent(nome)}`, { headers: authHeaders() });
        if (!res.ok) return;
        renderizarPessoas(await res.json());
        document.getElementById("paginacao-pessoas").innerHTML = "";
    }, 300);
}

function aplicarFiltroTipo() { document.getElementById("busca-nome").value = ""; offsetAtual = 0; carregarPessoas(); }

function renderizarPessoas(lista) {
    const isAdmin = ["sindico","admin"].includes(getSessao().perfil);
    const tbody = document.getElementById("tabela-pessoas");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999">Nenhuma pessoa.</td></tr>`; return; }
    lista.forEach(p => {
        const badge  = p.status === "DENTRO" ? `<span class="badge badge-dentro">DENTRO</span>` : `<span class="badge badge-fora">FORA</span>`;
        const fotoEl = p.foto ? `<div class="foto-mini"><img src="${p.foto}" /></div>` : `<div class="foto-mini">👤</div>`;
        const acoes  = isAdmin ? `<td><button class="btn-pequeno" onclick="abrirEditar('${p.documento}')">Editar</button> <button class="btn-pequeno btn-remover" onclick="removerPessoa('${p.documento}','${p.nome.replace(/'/g,"\\'")}')">Remover</button></td>` : `<td>—</td>`;
        tbody.innerHTML += `<tr><td>${fotoEl}</td><td>${p.nome}</td><td>${p.documento}</td><td>${p.tipo}</td><td>${p.quadra_lote||"—"}</td><td>${badge}</td>${acoes}</tr>`;
    });
}

function renderizarPaginacao() {
    const total = Math.ceil(totalPessoas / LIMIT), atual = Math.floor(offsetAtual / LIMIT);
    const el = document.getElementById("paginacao-pessoas");
    el.innerHTML = "";
    if (total <= 1) return;
    for (let i = 0; i < total; i++) {
        const btn = document.createElement("button");
        btn.textContent = i + 1;
        if (i === atual) btn.classList.add("ativa");
        btn.onclick = () => { offsetAtual = i * LIMIT; carregarPessoas(); };
        el.appendChild(btn);
    }
}

// ===== FOTO =====
function previewFoto(p) {
    const file = document.getElementById(`${p}-foto-input`).files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = e => {
        document.getElementById(`${p}-foto-preview`).innerHTML = `<img src="${e.target.result}" />`;
        if (p === "cad") fotoCadTemp = e.target.result;
        if (p === "edit") { fotoEditTemp = e.target.result; fotoEditRemover = false; }
    };
    reader.readAsDataURL(file);
}

function removerFotoEdicao() {
    fotoEditTemp = ""; fotoEditRemover = true;
    document.getElementById("edit-foto-preview").innerHTML = `<span>Sem foto</span>`;
    document.getElementById("edit-foto-input").value = "";
}

// ===== CADASTRAR =====
function toggleQuadraLote() {
    document.getElementById("campo-quadra-lote").style.display = document.getElementById("cad-tipo").value === "morador" ? "block" : "none";
}

async function cadastrar() {
    const nome = document.getElementById("cad-nome").value.trim();
    const documento = document.getElementById("cad-documento").value.trim();
    const tipo = document.getElementById("cad-tipo").value;
    const quadra = document.getElementById("cad-quadra").value.trim() || null;
    const lote = document.getElementById("cad-lote").value.trim() || null;
    if (!nome || !documento || !tipo) { mostrarMsg("Preencha nome, documento e tipo.", false); return; }
    const res = await fetch(`${API}/pessoas`, { method:"POST", headers:authHeaders(), body:JSON.stringify({nome,documento,tipo,quadra,lote,foto:fotoCadTemp||null}) });
    const data = await res.json();
    if (res.ok) {
        mostrarMsg(data.message, true);
        ["cad-nome","cad-documento","cad-quadra","cad-lote"].forEach(id => document.getElementById(id).value = "");
        document.getElementById("cad-tipo").value = "";
        document.getElementById("cad-foto-preview").innerHTML = "<span>Sem foto</span>";
        document.getElementById("cad-foto-input").value = "";
        document.getElementById("campo-quadra-lote").style.display = "none";
        fotoCadTemp = null;
    } else { mostrarMsg(data.detail || "Erro.", false); }
}

// ===== EDITAR =====
async function abrirEditar(documento) {
    const res = await fetch(`${API}/pessoas/${documento}`, { headers: authHeaders() });
    if (!res.ok) { mostrarMsg("Erro ao buscar.", false); return; }
    const p = await res.json();
    document.getElementById("edit-documento-original").value = p.documento;
    document.getElementById("edit-nome").value = p.nome;
    document.getElementById("edit-tipo").value = p.tipo;
    document.getElementById("edit-quadra-lote").value = p.quadra_lote || "";
    document.getElementById("edit-foto-preview").innerHTML = p.foto ? `<img src="${p.foto}" />` : `<span>Sem foto</span>`;
    document.getElementById("edit-foto-input").value = "";
    fotoEditTemp = null; fotoEditRemover = false;
    document.getElementById("modal-editar").style.display = "flex";
}

async function salvarEdicao() {
    const documento = document.getElementById("edit-documento-original").value;
    const body = { nome: document.getElementById("edit-nome").value.trim(), tipo: document.getElementById("edit-tipo").value, quadra_lote: document.getElementById("edit-quadra-lote").value.trim() || null };
    if (fotoEditRemover) body.foto = "";
    else if (fotoEditTemp) body.foto = fotoEditTemp;
    const res = await fetch(`${API}/pessoas/${documento}`, { method:"PUT", headers:authHeaders(), body:JSON.stringify(body) });
    const data = await res.json();
    fecharModal("modal-editar");
    if (res.ok) { mostrarMsg(data.message, true); carregarPessoas(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

async function removerPessoa(documento, nome) {
    if (!confirm(`Remover "${nome}"?`)) return;
    const res = await fetch(`${API}/pessoas/${documento}`, { method:"DELETE", headers:authHeaders() });
    const data = await res.json();
    if (res.ok) { mostrarMsg(data.message, true); carregarPessoas(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

// ===== BUSCA MOVIMENTO =====
function buscarParaMovimento(prefixo) {
    clearTimeout(buscaMovTimer[prefixo]);
    buscaMovTimer[prefixo] = setTimeout(async () => {
        const texto = document.getElementById(`${prefixo}-busca`).value.trim();
        const sugestoes = document.getElementById(`${prefixo}-sugestoes`);
        if (!texto) { sugestoes.innerHTML = ""; return; }
        let lista = [];
        const r1 = await fetch(`${API}/pessoas/busca?nome=${encodeURIComponent(texto)}`, { headers: authHeaders() });
        if (r1.ok) lista = await r1.json();
        const r2 = await fetch(`${API}/pessoas/${encodeURIComponent(texto)}`, { headers: authHeaders() });
        if (r2.ok) { const p = await r2.json(); if (!lista.find(x => x.documento === p.documento)) lista.unshift(p); }
        if (!lista.length) { sugestoes.innerHTML = `<div class="sugestao-item" style="color:#999">Nenhum resultado</div>`; return; }
        sugestoes.innerHTML = "";
        lista.slice(0, 8).forEach(p => {
            const fotoEl = p.foto ? `<div class="sugestao-foto"><img src="${p.foto}" /></div>` : `<div class="sugestao-foto">👤</div>`;
            const div = document.createElement("div");
            div.className = "sugestao-item";
            div.innerHTML = `${fotoEl}<div><strong>${p.nome}</strong><br><small>${p.documento} · ${p.tipo}</small></div>`;
            div.onclick = () => selecionarPessoa(prefixo, p);
            sugestoes.appendChild(div);
        });
    }, 250);
}

function selecionarPessoa(prefixo, p) {
    document.getElementById(`${prefixo}-documento`).value = p.documento;
    document.getElementById(`${prefixo}-busca`).value = p.nome;
    document.getElementById(`${prefixo}-sugestoes`).innerHTML = "";
    const fotoEl = p.foto ? `<div class="foto-mini"><img src="${p.foto}" /></div>` : `<div class="foto-mini">👤</div>`;
    const badge  = p.status === "DENTRO" ? `<span class="badge badge-dentro">DENTRO</span>` : `<span class="badge badge-fora">FORA</span>`;
    const el = document.getElementById(`${prefixo}-pessoa-selecionada`);
    el.style.display = "flex";
    el.innerHTML = `${fotoEl}<div><strong>${p.nome}</strong><br><small>${p.tipo} · ${p.quadra_lote||"—"}</small><br>${badge}</div>`;
}

// ===== ENTRADA =====
async function registrarEntrada() {
    const documento = document.getElementById("ent-documento").value.trim();
    if (!documento) { mostrarMsg("Selecione uma pessoa.", false); return; }
    const res = await fetch(`${API}/pessoas/${encodeURIComponent(documento)}`, { headers: authHeaders() });
    if (!res.ok) { mostrarMsg("Pessoa não encontrada.", false); return; }
    const p = await res.json();
    dadosEntradaPendente = { documento, quadra: document.getElementById("ent-quadra").value.trim()||null, lote: document.getElementById("ent-lote").value.trim()||null };
    const fotoEl = p.foto ? `<div class="foto-redonda"><img src="${p.foto}" /></div>` : `<div class="foto-redonda">👤</div>`;
    document.getElementById("confirmar-entrada-info").innerHTML = `${fotoEl}<div><strong style="font-size:16px">${p.nome}</strong><br>Documento: ${p.documento}<br>Tipo: ${p.tipo}</div>`;
    document.getElementById("modal-confirmar-entrada").style.display = "flex";
}

async function confirmarEntrada() {
    if (!dadosEntradaPendente) return;
    fecharModal("modal-confirmar-entrada");
    const res = await fetch(`${API}/entrada`, { method:"POST", headers:authHeaders(), body:JSON.stringify(dadosEntradaPendente) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) {
        document.getElementById("ent-busca").value = "";
        document.getElementById("ent-documento").value = "";
        document.getElementById("ent-quadra").value = "";
        document.getElementById("ent-lote").value = "";
        document.getElementById("ent-pessoa-selecionada").style.display = "none";
        carregarDashboard();
    }
    dadosEntradaPendente = null;
}

// ===== SAÍDA =====
async function registrarSaida() {
    const documento = document.getElementById("sai-documento").value.trim();
    if (!documento) { mostrarMsg("Selecione uma pessoa.", false); return; }
    const res = await fetch(`${API}/pessoas/${encodeURIComponent(documento)}`, { headers: authHeaders() });
    if (!res.ok) { mostrarMsg("Pessoa não encontrada.", false); return; }
    const p = await res.json();
    dadosSaidaPendente = { documento };
    const fotoEl = p.foto ? `<div class="foto-redonda"><img src="${p.foto}" /></div>` : `<div class="foto-redonda">👤</div>`;
    document.getElementById("confirmar-saida-info").innerHTML = `${fotoEl}<div><strong style="font-size:16px">${p.nome}</strong><br>Documento: ${p.documento}<br>Tipo: ${p.tipo}</div>`;
    document.getElementById("modal-confirmar-saida").style.display = "flex";
}

async function confirmarSaida() {
    if (!dadosSaidaPendente) return;
    fecharModal("modal-confirmar-saida");
    const res = await fetch(`${API}/saida`, { method:"POST", headers:authHeaders(), body:JSON.stringify(dadosSaidaPendente) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) {
        document.getElementById("sai-busca").value = "";
        document.getElementById("sai-documento").value = "";
        document.getElementById("sai-pessoa-selecionada").style.display = "none";
        carregarDashboard();
    }
    dadosSaidaPendente = null;
}

// ===== DENTRO =====
async function carregarDentro() {
    const res = await fetch(`${API}/pessoas/dentro`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-dentro");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#999">Ninguém dentro.</td></tr>`; return; }
    lista.forEach(p => {
        const fotoEl = p.foto ? `<div class="foto-mini"><img src="${p.foto}" /></div>` : `<div class="foto-mini">👤</div>`;
        tbody.innerHTML += `<tr><td>${fotoEl}</td><td>${p.nome}</td><td>${p.documento}</td><td>${p.tipo}</td><td>${p.quadra_lote||"—"}</td><td><button class="btn-pequeno" onclick="saidaRapida('${p.documento}','${p.nome.replace(/'/g,"\\'")}')">Saída</button></td></tr>`;
    });
}

async function saidaRapida(documento, nome) {
    if (!confirm(`Registrar saída de "${nome}"?`)) return;
    const res = await fetch(`${API}/saida`, { method:"POST", headers:authHeaders(), body:JSON.stringify({documento}) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) { carregarDentro(); carregarDashboard(); }
}

// ===== VEÍCULOS =====
async function carregarVeiculos() {
    const res = await fetch(`${API}/veiculos`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-veiculos");
    tbody.innerHTML = "";
    const isAdmin = ["sindico","admin"].includes(getSessao().perfil);
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999">Nenhum veículo cadastrado.</td></tr>`; return; }
    lista.forEach(v => {
        const badge = v.status === "DENTRO" ? `<span class="badge badge-dentro">DENTRO</span>` : `<span class="badge badge-fora">FORA</span>`;
        const acoes = isAdmin ? `<button class="btn-pequeno" onclick="abrirEditarVeiculo('${v.placa}')">Editar</button> <button class="btn-pequeno btn-remover" onclick="removerVeiculo('${v.placa}')">Remover</button>` : "—";
        tbody.innerHTML += `<tr><td><strong>${v.placa}</strong></td><td>${v.modelo||"—"}</td><td>${v.cor||"—"}</td><td>${v.empresa||"—"}</td><td>${v.pessoa_nome||"—"}</td><td>${badge}</td><td>${acoes}</td></tr>`;
    });
}

async function carregarVeiculosDentro() {
    const res = await fetch(`${API}/veiculos/dentro`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-veiculos-dentro");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#999">Nenhum veículo dentro.</td></tr>`; return; }
    lista.forEach(v => {
        tbody.innerHTML += `<tr><td><strong>${v.placa}</strong></td><td>${v.modelo||"—"}</td><td>${v.cor||"—"}</td><td>${v.empresa||"—"}</td><td>${v.pessoa_nome||"—"}</td><td><button class="btn-pequeno" onclick="saidaRapidaVeiculo('${v.placa}')">Saída</button></td></tr>`;
    });
}

function abrirModalVeiculo() {
    document.getElementById("modal-veiculo-titulo").textContent = "Cadastrar Veículo";
    document.getElementById("modal-veiculo-placa-original").value = "";
    document.getElementById("modal-veiculo-placa").disabled = false;
    ["modal-veiculo-placa","modal-veiculo-modelo","modal-veiculo-cor","modal-veiculo-empresa","modal-veiculo-responsavel"].forEach(id => document.getElementById(id).value = "");
    document.getElementById("modal-veiculo").style.display = "flex";
}

function abrirEditarVeiculo(placa) {
    fetch(`${API}/veiculos/${placa}`, { headers: authHeaders() }).then(r => r.json()).then(v => {
        document.getElementById("modal-veiculo-titulo").textContent = "Editar Veículo";
        document.getElementById("modal-veiculo-placa-original").value = placa;
        document.getElementById("modal-veiculo-placa").value = placa;
        document.getElementById("modal-veiculo-placa").disabled = true;
        document.getElementById("modal-veiculo-modelo").value = v.modelo || "";
        document.getElementById("modal-veiculo-cor").value = v.cor || "";
        document.getElementById("modal-veiculo-empresa").value = v.empresa || "";
        document.getElementById("modal-veiculo-responsavel").value = v.pessoa_documento || "";
        document.getElementById("modal-veiculo").style.display = "flex";
    });
}

async function salvarVeiculo() {
    const original = document.getElementById("modal-veiculo-placa-original").value;
    const placa    = document.getElementById("modal-veiculo-placa").value.trim().toUpperCase();
    const modelo   = document.getElementById("modal-veiculo-modelo").value.trim() || null;
    const cor      = document.getElementById("modal-veiculo-cor").value.trim() || null;
    const empresa  = document.getElementById("modal-veiculo-empresa").value.trim() || null;
    const pessoa_documento = document.getElementById("modal-veiculo-responsavel").value.trim() || null;
    if (!placa) { mostrarMsg("Placa é obrigatória.", false); return; }
    let res;
    if (!original) {
        res = await fetch(`${API}/veiculos`, { method:"POST", headers:authHeaders(), body:JSON.stringify({placa,modelo,cor,empresa,pessoa_documento}) });
    } else {
        res = await fetch(`${API}/veiculos/${original}`, { method:"PUT", headers:authHeaders(), body:JSON.stringify({modelo,cor,empresa,pessoa_documento}) });
    }
    const data = await res.json();
    fecharModal("modal-veiculo");
    if (res.ok) { mostrarMsg(data.message, true); carregarVeiculos(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

async function removerVeiculo(placa) {
    if (!confirm(`Remover veículo ${placa}?`)) return;
    const res = await fetch(`${API}/veiculos/${placa}`, { method:"DELETE", headers:authHeaders() });
    const data = await res.json();
    if (res.ok) { mostrarMsg(data.message, true); carregarVeiculos(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

async function entradaVeiculo() {
    const placa   = document.getElementById("veic-ent-placa").value.trim().toUpperCase();
    const destino = document.getElementById("veic-ent-destino").value.trim() || null;
    if (!placa) { mostrarMsg("Informe a placa.", false); return; }
    const res = await fetch(`${API}/veiculos/entrada`, { method:"POST", headers:authHeaders(), body:JSON.stringify({placa,destino}) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) { document.getElementById("veic-ent-placa").value = ""; document.getElementById("veic-ent-destino").value = ""; carregarDashboard(); }
}

async function saidaVeiculo() {
    const placa = document.getElementById("veic-sai-placa").value.trim().toUpperCase();
    if (!placa) { mostrarMsg("Informe a placa.", false); return; }
    const res = await fetch(`${API}/veiculos/saida`, { method:"POST", headers:authHeaders(), body:JSON.stringify({placa}) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) { document.getElementById("veic-sai-placa").value = ""; carregarDashboard(); }
}

async function saidaRapidaVeiculo(placa) {
    if (!confirm(`Registrar saída do veículo ${placa}?`)) return;
    const res = await fetch(`${API}/veiculos/saida`, { method:"POST", headers:authHeaders(), body:JSON.stringify({placa}) });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) { carregarVeiculosDentro(); carregarDashboard(); }
}

async function buscarRelatorioVeiculos() {
    const data = document.getElementById("veic-rel-data").value;
    if (!data) { mostrarMsg("Selecione uma data.", false); return; }
    const res = await fetch(`${API}/veiculos/relatorio?data=${data}`, { headers: authHeaders() });
    if (!res.ok) return;
    dadosRelatorioVeic = await res.json();
    const tbody = document.getElementById("tabela-veic-relatorio");
    tbody.innerHTML = "";
    if (!dadosRelatorioVeic.length) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999">Nenhum evento.</td></tr>`; return; }
    dadosRelatorioVeic.forEach(e => {
        const badge = e.acao === "entrada" ? `<span class="badge badge-entrada">ENTRADA</span>` : `<span class="badge badge-saida">SAÍDA</span>`;
        tbody.innerHTML += `<tr><td>${e.data_hora.replace("T"," ")}</td><td>${badge}</td><td>${e.placa}</td><td>${e.modelo||"—"}</td><td>${e.empresa||"—"}</td><td>${e.porteiro}</td><td>${e.destino||"—"}</td></tr>`;
    });
}

function exportarCSVVeiculos() {
    if (!dadosRelatorioVeic.length) { mostrarMsg("Nenhum dado.", false); return; }
    const cab = ["Horário","Ação","Placa","Modelo","Empresa","Porteiro","Destino"];
    const linhas = dadosRelatorioVeic.map(e => [e.data_hora.replace("T"," "),e.acao,e.placa,e.modelo||"",e.empresa||"",e.porteiro,e.destino||""]);
    gerarCSV(cab, linhas, `relatorio_veiculos_${document.getElementById("veic-rel-data").value}.csv`);
}

// ===== QR CODE =====
async function gerarQRCode() {
    const nome = document.getElementById("qr-nome").value.trim();
    const documento = document.getElementById("qr-documento").value.trim() || null;
    const destino = document.getElementById("qr-destino").value.trim() || null;
    const horas = parseInt(document.getElementById("qr-validade").value);
    if (!nome) { mostrarMsg("Nome do visitante é obrigatório.", false); return; }
    const res = await fetch(`${API}/qrcodes`, { method:"POST", headers:authHeaders(), body:JSON.stringify({nome_visitante:nome,documento_visitante:documento,destino,horas_validade:horas}) });
    const data = await res.json();
    if (!res.ok) { mostrarMsg(data.detail||"Erro.", false); return; }
    qrTokenAtual = data.token;
    document.getElementById("qr-resultado").style.display = "block";
    document.getElementById("qr-token-texto").textContent = `Token: ${data.token}`;
    // Gera QR Code usando API pública
    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(data.token)}`;
    document.getElementById("qr-imagem").innerHTML = `<img src="${qrUrl}" style="border-radius:8px" />`;
    mostrarMsg("QR Code gerado com sucesso!", true);
}

function copiarToken() {
    if (!qrTokenAtual) return;
    navigator.clipboard.writeText(qrTokenAtual).then(() => mostrarMsg("Token copiado!", true));
}

async function validarQRCode() {
    const token = document.getElementById("qr-validar-token").value.trim();
    if (!token) { mostrarMsg("Cole o token.", false); return; }
    const res = await fetch(`${API}/qrcodes/validar`, { method:"POST", headers:authHeaders(), body:JSON.stringify({token}) });
    const data = await res.json();
    const el = document.getElementById("qr-validar-resultado");
    if (res.ok) {
        el.innerHTML = `<div class="msg-ok" style="padding:12px;border-radius:6px">✅ ${data.message}<br><small>Visitante: ${data.dados.nome_visitante} | Destino: ${data.dados.destino||"—"}</small></div>`;
        mostrarMsg(data.message, true);
    } else {
        el.innerHTML = `<div class="msg-err" style="padding:12px;border-radius:6px">❌ ${data.detail}</div>`;
    }
}

async function carregarQRCodes() {
    const res = await fetch(`${API}/qrcodes`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-qrcodes");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#999">Nenhum QR Code gerado.</td></tr>`; return; }
    lista.forEach(q => {
        let statusBadge;
        if (q.usado) statusBadge = `<span class="badge badge-fora">Usado</span>`;
        else if (q.expirado) statusBadge = `<span class="badge badge-inativo">Expirado</span>`;
        else statusBadge = `<span class="badge badge-ativo">Válido</span>`;
        tbody.innerHTML += `<tr><td>${q.nome_visitante}</td><td>${q.destino||"—"}</td><td>${q.criado_por}</td><td>${q.expira_em.replace("T"," ")}</td><td>${statusBadge}</td></tr>`;
    });
}

// ===== RELATÓRIO =====
async function buscarRelatorio() {
    const data = document.getElementById("rel-data").value;
    if (!data) { mostrarMsg("Selecione uma data.", false); return; }
    const res = await fetch(`${API}/relatorio?data=${data}`, { headers: authHeaders() });
    if (!res.ok) return;
    dadosRelatorio = await res.json();
    const tbody = document.getElementById("tabela-relatorio");
    tbody.innerHTML = "";
    if (!dadosRelatorio.length) { tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999">Nenhum evento.</td></tr>`; return; }
    dadosRelatorio.forEach(e => {
        const badge = e.acao === "entrada" ? `<span class="badge badge-entrada">ENTRADA</span>` : `<span class="badge badge-saida">SAÍDA</span>`;
        tbody.innerHTML += `<tr><td>${e.data_hora.replace("T"," ")}</td><td>${badge}</td><td>${e.nome}</td><td>${e.documento}</td><td>${e.tipo}</td><td>${e.porteiro}</td><td>${e.destino||"—"}</td></tr>`;
    });
}

function exportarCSV() {
    if (!dadosRelatorio.length) { mostrarMsg("Nenhum dado.", false); return; }
    const cab = ["Horário","Ação","Nome","Documento","Tipo","Porteiro","Destino"];
    const linhas = dadosRelatorio.map(e => [e.data_hora.replace("T"," "),e.acao,e.nome,e.documento,e.tipo,e.porteiro,e.destino||""]);
    gerarCSV(cab, linhas, `relatorio_${document.getElementById("rel-data").value}.csv`);
}

function exportarPDF() {
    if (!dadosRelatorio.length) { mostrarMsg("Nenhum dado.", false); return; }
    const data = document.getElementById("rel-data").value;
    const s = getSessao();
    const linhas = dadosRelatorio.map(e => `<tr><td>${e.data_hora.replace("T"," ")}</td><td>${e.acao.toUpperCase()}</td><td>${e.nome}</td><td>${e.documento}</td><td>${e.tipo}</td><td>${e.porteiro}</td><td>${e.destino||"—"}</td></tr>`).join("");
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Relatório ${data}</title>
    <style>body{font-family:Arial;padding:24px}h1{color:#1e3a5f;margin-bottom:4px}p{color:#666;font-size:13px;margin-bottom:16px}table{width:100%;border-collapse:collapse;font-size:13px}th{background:#1e3a5f;color:white;padding:8px}td{padding:7px;border-bottom:1px solid #ddd}</style></head>
    <body><h1>Relatório de Movimentações</h1><p>${s.condominio_nome||"Condomínio"} — ${data}</p>
    <table><thead><tr><th>Horário</th><th>Ação</th><th>Nome</th><th>Documento</th><th>Tipo</th><th>Porteiro</th><th>Destino</th></tr></thead>
    <tbody>${linhas}</tbody></table></body></html>`;
    const blob = new Blob([html], { type: "text/html" });
    const url = URL.createObjectURL(blob);
    const win = window.open(url, "_blank");
    setTimeout(() => { win.print(); URL.revokeObjectURL(url); }, 500);
}

function gerarCSV(cab, linhas, nome) {
    const csv = [cab, ...linhas].map(l => l.map(v => `"${v}"`).join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = nome; a.click();
}

// ===== EQUIPE =====
async function carregarEquipe() {
    const res = await fetch(`${API}/usuarios`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-usuarios");
    tbody.innerHTML = "";
    lista.forEach(u => {
        const perfil = { sindico:`<span class="badge badge-admin">Síndico</span>`, admin:`<span class="badge badge-porteiro">Admin</span>`, porteiro:`<span class="badge" style="background:#eee;color:#555">Porteiro</span>` }[u.perfil] || u.perfil;
        const status = u.ativo ? `<span class="badge badge-ativo">Ativo</span>` : `<span class="badge badge-inativo">Desativado</span>`;
        const ehEu = u.usuario === getSessao().usuario;
        tbody.innerHTML += `<tr><td>${u.usuario}${ehEu?" <small>(você)</small>":""}</td><td>${perfil}</td><td>${status}</td><td>${(u.criado_em||"").replace("T"," ")}</td>
        <td><button class="btn-pequeno" onclick="abrirEditarUsuario('${u.usuario}','${u.perfil}',${u.ativo})">Editar</button>${!ehEu?`<button class="btn-pequeno btn-remover" onclick="removerUsuario('${u.usuario}')">Remover</button>`:""}</td></tr>`;
    });
}

function abrirModalNovoUsuario() {
    document.getElementById("modal-usuario-titulo").textContent = "Novo membro";
    document.getElementById("modal-usuario-original").value = "";
    document.getElementById("modal-usuario-nome").value = "";
    document.getElementById("modal-usuario-nome").disabled = false;
    document.getElementById("modal-usuario-senha").value = "";
    document.getElementById("modal-senha-label").textContent = "Senha *";
    document.getElementById("modal-usuario-perfil").value = "porteiro";
    document.getElementById("modal-ativo-grupo").style.display = "none";
    document.getElementById("modal-usuario").style.display = "flex";
}

function abrirEditarUsuario(usuario, perfil, ativo) {
    document.getElementById("modal-usuario-titulo").textContent = "Editar membro";
    document.getElementById("modal-usuario-original").value = usuario;
    document.getElementById("modal-usuario-nome").value = usuario;
    document.getElementById("modal-usuario-nome").disabled = true;
    document.getElementById("modal-usuario-senha").value = "";
    document.getElementById("modal-senha-label").textContent = "Nova senha (vazio = manter)";
    document.getElementById("modal-usuario-perfil").value = perfil;
    document.getElementById("modal-usuario-ativo").value = String(ativo);
    document.getElementById("modal-ativo-grupo").style.display = "block";
    document.getElementById("modal-usuario").style.display = "flex";
}

async function salvarUsuario() {
    const original = document.getElementById("modal-usuario-original").value;
    const usuario  = document.getElementById("modal-usuario-nome").value.trim();
    const senha    = document.getElementById("modal-usuario-senha").value.trim();
    const perfil   = document.getElementById("modal-usuario-perfil").value;
    const ativo    = parseInt(document.getElementById("modal-usuario-ativo").value || "1");
    let res;
    if (!original) {
        if (!usuario || !senha) { mostrarMsg("Usuário e senha obrigatórios.", false); return; }
        res = await fetch(`${API}/usuarios`, { method:"POST", headers:authHeaders(), body:JSON.stringify({usuario,senha,perfil}) });
    } else {
        const body = { perfil, ativo }; if (senha) body.nova_senha = senha;
        res = await fetch(`${API}/usuarios/${original}`, { method:"PUT", headers:authHeaders(), body:JSON.stringify(body) });
    }
    const data = await res.json();
    fecharModal("modal-usuario");
    if (res.ok) { mostrarMsg(data.message, true); carregarEquipe(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

async function removerUsuario(usuario) {
    if (!confirm(`Remover "${usuario}"?`)) return;
    const res = await fetch(`${API}/usuarios/${usuario}`, { method:"DELETE", headers:authHeaders() });
    const data = await res.json();
    if (res.ok) { mostrarMsg(data.message, true); carregarEquipe(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

// ===== CONFIGURAÇÕES =====
async function carregarConfiguracoes() {
    const res = await fetch(`${API}/dashboard`, { headers: authHeaders() });
    if (!res.ok) return;
    const d = await res.json();
    if (d.condominio) {
        document.getElementById("conf-nome").value     = d.condominio.nome || "";
        document.getElementById("conf-endereco").value = d.condominio.endereco || "";
    }
}

async function trocarSenha() {
    const atual    = document.getElementById("senha-atual").value.trim();
    const nova     = document.getElementById("senha-nova").value.trim();
    const confirma = document.getElementById("senha-confirma").value.trim();
    if (!atual || !nova) { mostrarMsg("Preencha todos os campos.", false); return; }
    if (nova !== confirma) { mostrarMsg("As senhas não conferem.", false); return; }
    const res = await fetch(`${API}/trocar-senha`, { method:"POST", headers:authHeaders(), body:JSON.stringify({senha_atual:atual,nova_senha:nova}) });
    const data = await res.json();
    if (res.ok) {
        mostrarMsg(data.message, true);
        // Atualiza sessão com nova senha
        sessionStorage.setItem("senha", nova);
        document.getElementById("senha-atual").value = "";
        document.getElementById("senha-nova").value = "";
        document.getElementById("senha-confirma").value = "";
    } else { mostrarMsg(data.detail || "Erro.", false); }
}

async function fazerBackup() {
    const res = await fetch(`${API}/backup`, { method:"POST", headers:authHeaders() });
    const data = await res.json();
    mostrarMsg(res.ok ? data.message : (data.detail||"Erro."), res.ok);
    if (res.ok) carregarBackups();
}

async function carregarBackups() {
    const res = await fetch(`${API}/backups`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-backups");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="2" style="text-align:center;color:#999">Nenhum backup ainda.</td></tr>`; return; }
    lista.forEach(b => { tbody.innerHTML += `<tr><td>${b.nome}</td><td>${b.tamanho_kb} KB</td></tr>`; });
}

async function carregarLog() {
    const res = await fetch(`${API}/log-admin?limit=50`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-log");
    tbody.innerHTML = "";
    if (!lista.length) { tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:#999">Nenhuma ação.</td></tr>`; return; }
    lista.forEach(l => { tbody.innerHTML += `<tr><td>${l.data_hora.replace("T"," ")}</td><td>${l.usuario}</td><td>${l.acao.replace(/_/g," ")}</td><td>${l.detalhe||"—"}</td></tr>`; });
}
