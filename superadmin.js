window.addEventListener("DOMContentLoaded", () => {
    if (!exigirLogin(["superadmin"])) return;
    const s = getSessao();
    document.getElementById("usuario-logado").textContent = `👤 ${s.usuario}`;
    carregarDashboard();
});

function mostrarAba(nome, btn) {
    document.querySelectorAll(".aba-conteudo").forEach(el => el.style.display = "none");
    document.querySelectorAll(".aba").forEach(el => el.classList.remove("ativa"));
    document.getElementById(`aba-${nome}`).style.display = "block";
    btn.classList.add("ativa");

    if (nome === "dashboard")   carregarDashboard();
    if (nome === "condominios") carregarCondominios();
    if (nome === "usuarios")    carregarTodosUsuarios();
    if (nome === "log")         carregarLog();
}

// ================================================================
// DASHBOARD
// ================================================================
async function carregarDashboard() {
    const res = await fetch(`${API}/super/dashboard`, { headers: authHeaders() });
    if (!res.ok) return;
    const d = await res.json();

    document.getElementById("stat-total-cond").textContent = d.total_condominios;
    document.getElementById("stat-ativos").textContent     = d.condominios_ativos;
    document.getElementById("stat-inativos").textContent   = d.condominios_inativos;

    const tbody = document.getElementById("tabela-dash-cond");
    tbody.innerHTML = "";
    if (!d.condominios.length) {
        tbody.innerHTML = `<tr><td colspan="6" style="text-align:center;color:#999">Nenhum condomínio cadastrado.</td></tr>`;
        return;
    }
    d.condominios.forEach(c => {
        const status = c.ativo
            ? `<span class="badge badge-ativo">Ativo</span>`
            : `<span class="badge badge-inativo">Inativo</span>`;
        tbody.innerHTML += `<tr>
            <td>${c.nome}</td>
            <td><small style="color:#888">${c.slug}</small></td>
            <td>${c.total_pessoas ?? "—"}</td>
            <td>${c.total_usuarios ?? "—"}</td>
            <td>${status}</td>
            <td>${(c.criado_em||"").replace("T"," ")}</td>
        </tr>`;
    });
}

// ================================================================
// CONDOMÍNIOS
// ================================================================
async function carregarCondominios() {
    const res = await fetch(`${API}/super/condominios`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-condominios");
    tbody.innerHTML = "";
    if (!lista.length) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align:center;color:#999">Nenhum condomínio.</td></tr>`;
        return;
    }
    lista.forEach(c => {
        const status = c.ativo
            ? `<span class="badge badge-ativo">Ativo</span>`
            : `<span class="badge badge-inativo">Inativo</span>`;
        tbody.innerHTML += `<tr>
            <td>${c.nome}</td>
            <td>${c.endereco||"—"}</td>
            <td>${c.total_pessoas ?? "—"}</td>
            <td>${c.total_usuarios ?? "—"}</td>
            <td>${status}</td>
            <td>${(c.criado_em||"").replace("T"," ")}</td>
            <td>
                <button class="btn-pequeno" onclick="abrirEditarCond(${c.id},'${c.nome.replace(/'/g,"\\'")}','${(c.endereco||"").replace(/'/g,"\\'")}',${c.ativo})">Editar</button>
            </td>
        </tr>`;
    });
}

function abrirEditarCond(id, nome, endereco, ativo) {
    document.getElementById("modal-cond-id").value       = id;
    document.getElementById("modal-cond-nome").value     = nome;
    document.getElementById("modal-cond-endereco").value = endereco;
    document.getElementById("modal-cond-ativo").value    = String(ativo);
    document.getElementById("modal-cond").style.display  = "flex";
}

async function salvarCondominio() {
    const id       = document.getElementById("modal-cond-id").value;
    const nome     = document.getElementById("modal-cond-nome").value.trim();
    const endereco = document.getElementById("modal-cond-endereco").value.trim() || null;
    const ativo    = parseInt(document.getElementById("modal-cond-ativo").value);

    const res = await fetch(`${API}/super/condominios/${id}`, {
        method: "PUT", headers: authHeaders(),
        body: JSON.stringify({ nome, endereco, ativo })
    });
    const data = await res.json();
    fecharModal("modal-cond");
    if (res.ok) { mostrarMsg(data.message, true); carregarCondominios(); carregarDashboard(); }
    else { mostrarMsg(data.detail || "Erro.", false); }
}

// ================================================================
// TODOS OS USUÁRIOS
// ================================================================
async function carregarTodosUsuarios() {
    const res = await fetch(`${API}/super/usuarios`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-todos-usuarios");
    tbody.innerHTML = "";
    if (!lista.length) {
        tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;color:#999">Nenhum usuário.</td></tr>`;
        return;
    }
    lista.forEach(u => {
        const perfis = {
            superadmin: `<span class="badge" style="background:#2c3e50;color:white">Superadmin</span>`,
            sindico:    `<span class="badge badge-admin">Síndico</span>`,
            admin:      `<span class="badge badge-porteiro">Admin</span>`,
            porteiro:   `<span class="badge" style="background:#eee;color:#555">Porteiro</span>`,
        };
        const status = u.ativo
            ? `<span class="badge badge-ativo">Ativo</span>`
            : `<span class="badge badge-inativo">Desativado</span>`;
        tbody.innerHTML += `<tr>
            <td>${u.usuario}</td>
            <td>${perfis[u.perfil] || u.perfil}</td>
            <td>${u.condominio_nome || "<span style='color:#aaa'>—</span>"}</td>
            <td>${status}</td>
            <td>${(u.criado_em||"").replace("T"," ")}</td>
        </tr>`;
    });
}

// ================================================================
// LOG GERAL
// ================================================================
async function carregarLog() {
    const res = await fetch(`${API}/super/log?limit=100`, { headers: authHeaders() });
    if (!res.ok) return;
    const lista = await res.json();
    const tbody = document.getElementById("tabela-log-geral");
    tbody.innerHTML = "";
    if (!lista.length) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align:center;color:#999">Nenhuma ação registrada.</td></tr>`;
        return;
    }
    lista.forEach(l => {
        tbody.innerHTML += `<tr>
            <td>${l.data_hora.replace("T"," ")}</td>
            <td>${l.usuario}</td>
            <td>${l.acao.replace(/_/g," ")}</td>
            <td>${l.detalhe||"—"}</td>
        </tr>`;
    });
}
