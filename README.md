Portaria Pro — Sistema de Controle de Acesso para Condomínios

Sistema completo de portaria como SaaS (Software as a Service), desenvolvido para gerenciar o controle de acesso de condomínios com múltiplos perfis de usuário, controle de veículos, QR Code para visitantes e muito mais.

---

Funcionalidades

- **Multi-tenant** — cada condomínio tem seus dados isolados
- **Perfis de acesso** — Superadmin, Síndico, Admin e Porteiro
- **Cadastro de pessoas** — moradores, visitantes, prestadores e entregadores
- **Controle de entrada e saída** com confirmação visual e foto
- **Controle de veículos** — entrada, saída e histórico por placa
- **QR Code para visitantes** — pré-autorização com validade configurável
- **Dashboard em tempo real** — pessoas e veículos dentro, movimentações do dia
- **Relatórios** — exportação em CSV e PDF
- **Backup automático** do banco de dados
- **Busca por nome** com sugestões em tempo real
- **Fotos** no cadastro de pessoas
- **Log de ações** administrativas completo

---

Tecnologias

**Backend**
- Python 3.11+
- FastAPI
- SQLite
- Pydantic
- Uvicorn

**Frontend**
- HTML5, CSS3, JavaScript puro
- Sem frameworks — leve e rápido

---

Estrutura do projeto

```
Portaria-Saas/
├── backend/
│   ├── api.py          # Endpoints da API REST
│   ├── database.py     # Banco de dados SQLite
│   ├── services.py     # Regras de negócio
│   ├── models.py       # Modelos Pydantic
│   ├── main.py         # Interface CLI (terminal)
│   └── requirements.txt
└── frontend/
    ├── index.html      # Tela de login
    ├── register.html   # Cadastro de condomínio
    ├── painel.html     # Painel principal
    ├── superadmin.html # Painel master
    ├── config.js       # URL da API
    ├── auth.js         # Helpers de autenticação
    ├── painel.js       # Lógica do painel
    ├── superadmin.js   # Lógica do superadmin
    └── style.css       # Estilos
```



Desenvolvido com 💙
