// Helpers de autenticação usados em todas as páginas

function getSessao() {
    return {
        usuario:        sessionStorage.getItem("usuario"),
        senha:          sessionStorage.getItem("senha"),
        perfil:         sessionStorage.getItem("perfil"),
        condominio_id:  sessionStorage.getItem("condominio_id"),
        condominio_nome: sessionStorage.getItem("condominio_nome"),
    };
}

function authHeaders() {
    const s = getSessao();
    return {
        "Authorization": "Basic " + btoa(`${s.usuario}:${s.senha}`),
        "Content-Type": "application/json"
    };
}

function exigirLogin(perfisPermitidos = []) {
    const s = getSessao();
    if (!s.usuario || !s.senha) {
        window.location.href = "index.html";
        return false;
    }
    if (perfisPermitidos.length && !perfisPermitidos.includes(s.perfil)) {
        window.location.href = "index.html";
        return false;
    }
    return true;
}

function sair() {
    sessionStorage.clear();
    window.location.href = "index.html";
}

// Mensagem global
function mostrarMsg(texto, ok = true) {
    const el = document.getElementById("msg-global");
    if (!el) return;
    el.textContent = texto;
    el.className = ok ? "msg-ok" : "msg-err";
    setTimeout(() => { el.textContent = ""; el.className = ""; }, 4000);
}

function fecharModal(id) {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
}

// Fecha modal clicando fora
document.addEventListener("click", e => {
    document.querySelectorAll(".modal").forEach(modal => {
        if (e.target === modal) modal.style.display = "none";
    });
});
