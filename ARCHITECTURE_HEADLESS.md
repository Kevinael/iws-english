# Arquitetura — IWS com e sem Streamlit

Este documento explica como o simulador IWS funciona em **dois modos**:

1. **Com Streamlit** — o aplicativo web interativo completo (`streamlit run IWS_UI.py`).
2. **Sem Streamlit** — a camada de cálculo (`core/`) usada diretamente em
   scripts, notebooks, testes ou CI, sem subir o framework web.

O ponto central: **`core/` não depende de Streamlit**. A interface depende do
núcleo, nunca o contrário.

---

## 1. Camadas e direção de dependência

```
┌──────────────────────────────────────────────────────────┐
│  CAMADA DE UI  (depende de Streamlit)                      │
│                                                            │
│  IWS_UI.py          orquestrador, page_config, roteamento  │
│  ui/                clean_view, theme, theory/, theory_dc   │
│  ui_components/     sim_config, sim_results, sim_runner,    │
│                     tim_fault_ui, ...                       │
└───────────────────────────┬──────────────────────────────┘
                            │ importa e chama (seta única)
                            ▼
┌──────────────────────────────────────────────────────────┐
│  CAMADA DE NÚCLEO  (ZERO Streamlit)                        │
│                                                            │
│  core/tim/   modelo dq0, solver LSODA, fontes, falhas,     │
│              estimadores, análise harmônica/energética     │
│  core/dc/    modelo CC, solver, fontes, estimadores        │
│  core/       transforms, constants, session_schema         │
│                                                            │
│  recebe parâmetros  →  devolve arrays NumPy (só números)   │
└──────────────────────────────────────────────────────────┘
```

**Regra de ouro:** a dependência é uma seta de mão única — `ui → core`.
A UI importa o núcleo; o núcleo nunca importa a UI nem o Streamlit.

### O que "sem Streamlit" significa

Não significa remover o app. Significa que o **núcleo não _depende_ de
Streamlit** — é possível calcular sem o framework web instalado ou rodando.
Analogia: o motor de um carro gira numa bancada sem o painel. O painel mostra a
rotação do motor; o motor não precisa do painel para funcionar.

### Verificação objetiva

`core/` é livre de Streamlit, comprovado por três testes:

1. **Estático** — `grep streamlit core/` retorna **zero** ocorrências (nem
   `import`, nem comentário, nem docstring).
2. **Dinâmico** — `import core` não carrega `streamlit` em `sys.modules`.
3. **Bloqueio forçado** — com `streamlit` proibido no `sys.meta_path`, os
   **23 módulos de `core/` importam sem falha**. Se algum dependesse de
   Streamlit, falharia imediatamente.

---

## 2. Modo COM Streamlit (aplicativo web)

```bash
streamlit run IWS_UI.py
```

Abre em `http://localhost:8501`. Fluxo:

1. `IWS_UI.py` configura a página e resolve a máquina via `_MACHINE_REGISTRY`
   (MIT ou MCC).
2. A camada UI (`ui_components/sim_config*`) renderiza os widgets de parâmetros
   e experimento.
3. Ao clicar **Run Simulation**, `sim_runner*` monta os parâmetros e chama o
   **núcleo** (`core.tim.facade.run_simulation` ou
   `core.dc.facade.run_simulation_dc`).
4. O núcleo integra o modelo e devolve um `dict` de arrays NumPy.
5. A camada UI (`sim_results*` + `viz/`) desenha gráficos Plotly e tabelas.

A UI só **orquestra e desenha**. Toda a física vive no núcleo.

---

## 3. Modo SEM Streamlit (uso programático)

O núcleo é uma biblioteca Python comum. A API pública estável fica nas
**fachadas**:

- `core.tim.facade` — máquina de indução (MIT): `MachineParams`,
  `run_simulation`, `build_fns`.
- `core.dc.facade` — máquina CC (MCC): `DCMachineParams`, `run_simulation_dc`,
  `make_voltage_fn_dc`, `make_torque_fn_dc`, `estimate_dc_nameplate`,
  `estimate_dc_tests`.

### Exemplo MIT (partida direta — DOL)

```python
from core.tim.facade import MachineParams, run_simulation, build_fns

mp  = MachineParams(Vl=220.0, f=60.0, p=4)        # parâmetros da máquina
cfg = {"exp_type": "dol", "Tl_final": 10.0, "t_carga": 0.5}

vfn, tfn, t_ev = build_fns(cfg, mp)               # fontes de tensão/torque
res = run_simulation(mp, tmax=1.0, h=1e-4,
                     voltage_fn=vfn, torque_fn=tfn)

print(res["n"][-1])    # velocidade final (RPM)  -> ~1780
print(res.keys())      # 53 arrays: t, n, Te, ias, ibs, ics, ...
```

`res` é um `dict[str, np.ndarray]` — apenas números, sem tela. Pode alimentar
matplotlib, pandas, um relatório, um teste, ou um endpoint de API.

### Exemplo MCC (motor CC)

```python
from core.dc.facade import (
    DCMachineParams, run_simulation_dc,
    make_voltage_fn_dc, make_torque_fn_dc,
)

mp  = DCMachineParams(Va=24.0, Ra=0.013, La=0.001, kb=0.004,
                      excitation="sep_motor")
vfn = make_voltage_fn_dc(mp, exp_config={...})
tfn = make_torque_fn_dc(mp, exp_config={...})
res = run_simulation_dc(mp, tmax=12.0, h=1e-3,
                        voltage_fn=vfn, torque_fn=tfn)
```

### Casos de uso desbloqueados

- **Notebooks Jupyter** — explorar simulações sem subir o servidor web.
- **CI / testes** — a suíte de física (`tests/`) roda sem Streamlit, rápida e
  isolada (`pytest tests/`).
- **Scripts batch** — varreduras de parâmetros, geração de datasets.
- **Outra UI no futuro** — API REST, CLI ou GUI alternativa reusam o mesmo
  núcleo sem reescrever a física.

---

## 4. A exceção controlada: `ui_components/tim_fault_ui.py`

As funções de UI dos modelos de falha (`render_desequilibrio_ui`,
`render_broken_bar_ui`) **eram** parte de `core/tim/fault.py`. Foram movidas
para `ui_components/tim_fault_ui.py`, deixando o núcleo limpo.

A **física** das falhas permanece no núcleo, pura:

- `core/tim/fault_model.py` — `abc_voltages_deseq` (tensões desequilibradas /
  falta de fase) e `make_broken_bar_rr_fn` (modulação de Rr para barra
  quebrada). Importadas por `solver`, `machine_model` e `facade`.

Assim, a física de falhas é simulável sem Streamlit; apenas os painéis
interativos vivem na camada de UI.

---

## 5. Resumo

| Pergunta | Resposta |
|---|---|
| `core/` depende de Streamlit? | **Não** |
| `import core` carrega Streamlit? | **Não** |
| O app web continua funcionando? | **Sim**, inalterado |
| Dá para simular sem Streamlit? | **Sim**, via `core.tim.facade` / `core.dc.facade` |
| Quem depende de quem? | `ui → core` (seta única) |

O simulador funciona **com** Streamlit (app web interativo) e **sem** Streamlit
(biblioteca de cálculo), porque a física foi desacoplada do framework de UI.
