# -*- coding: utf-8 -*-
"""
desequilibrio_falta.py
======================
Módulo reservado para simulação de desequilíbrio de tensão e falta de fase.
Não é importado nem utilizado pelo restante da aplicação.

Para reativar: importe render_desequilibrio_ui em IWS_UI.py e adicione
deseq_a, deseq_b, deseq_c, falta_fase_a, falta_fase_b, falta_fase_c
como parâmetros de run_simulation em IWS_PY.py.
"""
from __future__ import annotations
import math
import numpy as np


# ── Geração de tensões com desequilíbrio/falta ──────────────────────────────

def abc_voltages_deseq(t, Vl: float, f: float,
                       deseq_a: float = 0.0,
                       deseq_b: float = 0.0,
                       deseq_c: float = 0.0,
                       falta_fase_a: bool = False,
                       falta_fase_b: bool = False,
                       falta_fase_c: bool = False,
                       df_a: float = 0.0,
                       df_b: float = 0.0,
                       df_c: float = 0.0):
    """Gera tensões abc com desequilíbrio e/ou falta de fase em qualquer fase.

    deseq_a / deseq_b / deseq_c : desvio fracional em Vl (ex: 0.1 = +10%, -0.1 = -10%).
    falta_fase_a/b/c             : se True, força a tensão da fase a zero.
    df_a / df_b / df_c           : desvio de frequência por fase em Hz (0 = nominal).
    Aceita t escalar ou np.ndarray; retorna o mesmo tipo.
    """
    scalar = np.ndim(t) == 0
    t_arr  = np.atleast_1d(np.asarray(t, dtype=float))
    zero   = np.zeros_like(t_arr)
    k      = np.sqrt(2.0 / 3.0)

    tetae_a = 2.0 * np.pi * (f + df_a) * t_arr
    tetae_b = 2.0 * np.pi * (f + df_b) * t_arr
    tetae_c = 2.0 * np.pi * (f + df_c) * t_arr

    Va = zero if falta_fase_a else k * Vl * (1.0 + deseq_a) * np.sin(tetae_a)
    Vb = zero if falta_fase_b else k * Vl * (1.0 + deseq_b) * np.sin(tetae_b - 2.0 * np.pi / 3.0)
    Vc = zero if falta_fase_c else k * Vl * (1.0 + deseq_c) * np.sin(tetae_c + 2.0 * np.pi / 3.0)

    if scalar:
        return float(Va[0]), float(Vb[0]), float(Vc[0])
    return Va, Vb, Vc


# ── Modelo de Barra Quebrada ─────────────────────────────────────────────────

def make_broken_bar_rr_fn(Rr_nominal: float, severity: float, wb: float,
                          t_start: float = 0.0):
    """Retorna função Rr(t, theta_slip) que modula Rr à freq. de escorregamento a partir de t_start.

    Modelo: Rr(t) = Rr0 · (1 + α · cos(2·θ_slip))  para t >= t_start
            Rr(t) = Rr0                               para t <  t_start

    Args:
        Rr_nominal: resistência nominal do rotor (Ω).
        severity:   α — amplitude da oscilação (0 = saudável, 0.1 = 10% de quebra).
        wb:         frequência angular base (rad/s).
        t_start:    instante de início da falha (s). 0 = falha presente desde o início.

    Returns:
        Callable[[float, float], float] — (t, theta_slip) → Rr efetivo.
        Se severity == 0, retorna None (sinal para desativar o modelo).
    """
    if severity == 0.0:
        return None

    def _rr_fn(t: float, theta_slip: float) -> float:
        if t < t_start:
            return Rr_nominal
        return Rr_nominal * (1.0 + severity * math.cos(2.0 * theta_slip))

    return _rr_fn


# ── Bloco de UI ─────────────────────────────────────────────────────────────

def render_desequilibrio_ui(config: dict, tmax: float = 2.0) -> None:
    """Renderiza o expander de desequilíbrio de tensão / falta de fase.

    Preenche config com as chaves:
      deseq_a, deseq_b, deseq_c,
      falta_fase_a, falta_fase_b, falta_fase_c,
      t_deseq.
    Deve ser chamado dentro do bloco de configuração do experimento em IWS_UI.py.
    """
    import streamlit as st
    st.write("")
    with st.expander("Desequilíbrio de Tensão / Falta de Fase", expanded=False):
        st.info("Simula assimetria na rede. Útil para estudar diagnóstico de falhas e proteção de motores.")

        with st.expander("O que é desequilíbrio de tensão? (teoria, normas e dicas)", expanded=False):
            st.markdown("""
**Definição.** Um sistema trifásico é considerado **desequilibrado** quando os três fasores
de tensão de linha não possuem **módulos iguais** e/ou não estão **defasados de 120°** entre si.

**Causas comuns:**
- Cargas monofásicas distribuídas de forma assimétrica no alimentador.
- Bancos de capacitores ou transformadores com tensões de tap desalinhadas.
- Conexões deficientes (terminais oxidados, fusíveis abertos parcialmente).
- Faltas monofásicas (curto-circuito fase-terra) durante o transitório.

**Decomposição em componentes simétricas (Fortescue).** Qualquer terna desequilibrada
pode ser decomposta em três sistemas balanceados:

| Componente | Símbolo | Característica | Efeito no motor |
|-----------|---------|---------------|-----------------|
| Positiva | $V_1$ | Sequência ABC normal | Produz torque útil |
| Negativa | $V_2$ | Sequência ACB (campo girante reverso) | Gera torque **frenante** e correntes elevadas |
| Zero | $V_0$ | Três fasores em fase | Circula apenas se houver neutro acessível |

A componente de **sequência negativa** é a principal responsável pelos danos: ela
enxerga um escorregamento próximo de $2 - s \\approx 2$ (campo gira contra o rotor),
gerando correntes ~5–6× a componente equivalente em sequência positiva.

**Fator de desequilíbrio de tensão (VUF, NEMA MG-1 §14.36):**
$$\\text{VUF}_{\\%} = \\frac{\\text{máximo desvio de }V_l\\text{ em relação à média}}{\\text{média de }V_l} \\times 100\\%$$

**Limites normativos:**
- **NEMA MG-1:** motores devem operar com VUF ≤ **1%** sem derating. Acima disso, aplica-se fator de redução de potência (curva da NEMA).
- **ANEEL PRODIST Módulo 8:** limite de **2%** em conexões BT (≤ 1 kV) e **3%** em MT/AT.
- **IEC 60034-1:** limite de **1%** contínuo, com excursões transitórias toleradas.

**Impactos típicos no motor:**
- Aquecimento adicional: $\\Delta T \\propto \\text{VUF}^2$ — um VUF de 3,5% pode aumentar a temperatura dos enrolamentos em ~25%, reduzindo a vida útil pela metade.
- Torque eletromagnético com **oscilação de 2·f** (120 Hz em rede 60 Hz) devido à interação entre campos de sequência positiva e negativa.
- Redução do torque máximo disponível.
- Aumento de vibração e ruído audível.

**Como configurar este painel:**
- **Desvio de amplitude (%):** modifica o módulo de $V_a$, $V_b$ ou $V_c$ individualmente, em relação ao nominal. Use valores pequenos (1–5%) para simular desequilíbrio típico de rede; valores maiores (10–30%) para estudar a região de proteção.
- **Desvio de frequência (Hz):** raro em sistemas reais (rede está sincronizada), mas útil para simular geradores isolados ou inversores fora de sincronismo.
- **Falta de fase:** força $V_a$, $V_b$ ou $V_c$ a zero. **Aviso:** uma falta de fase eleva a corrente nas fases remanescentes para 1,7–2,5× o nominal — proteja com tempo de simulação curto (≤ 1 s).
- **Instante de início:** o sistema parte da rede balanceada e o desequilíbrio é aplicado a partir deste instante. Use 0 para aplicar desde o início, ou um valor após o regime permanente para visualizar o transitório de desequilíbrio.

**Como observar os efeitos:**
- Gráficos de **correntes de fase $i_{as}, i_{bs}, i_{cs}$**: amplitudes desiguais.
- **Torque eletromagnético $T_e$**: oscilação visível em 2·f sobreposta ao valor médio.
- **Velocidade $n$**: pequena oscilação na velocidade (atenuada pela inércia).
- **Análise FFT do torque**: pico em 120 Hz (rede 60 Hz) confirma sequência negativa.

**Referências:**
- NEMA MG-1, *Motors and Generators*, §14.36 ("Effects of Unbalanced Voltage on Motor Performance").
- ANEEL PRODIST, *Módulo 8 — Qualidade da Energia Elétrica*, §3.4.
- IEC 60034-1, *Rotating Electrical Machines — Rating and Performance*, §7.2.
- Fitzgerald/Umans, *Máquinas Elétricas*, §4.7 ("Componentes Simétricas").
            """)

        col_a, col_b, col_c = st.columns(3)

        with col_a:
            st.markdown("**Fase A**")
            deseq_a = st.slider(
                "Desvio amplitude A (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: +10 → Va = 1.1 × Vnominal", key="deseq_a"
            ) / 100.0
            df_a = float(st.slider(
                "Desvio frequência A (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Va. 0 = nominal.", key="df_a"
            ))
            falta_a = st.toggle("Falta de Fase A (Va = 0)", value=False, key="falta_a")
            if falta_a:
                st.warning("Falta na fase A — correntes muito elevadas.")

        with col_b:
            st.markdown("**Fase B**")
            deseq_b = st.slider(
                "Desvio amplitude B (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: +10 → Vb = 1.1 × Vnominal", key="deseq_b"
            ) / 100.0
            df_b = float(st.slider(
                "Desvio frequência B (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Vb. 0 = nominal.", key="df_b"
            ))
            falta_b = st.toggle("Falta de Fase B (Vb = 0)", value=False, key="falta_b")
            if falta_b:
                st.warning("Falta na fase B — correntes muito elevadas.")

        with col_c:
            st.markdown("**Fase C**")
            deseq_c = st.slider(
                "Desvio amplitude C (%)", min_value=-30, max_value=30, value=0, step=1,
                help="Ex: -10 → Vc = 0.9 × Vnominal", key="deseq_c"
            ) / 100.0
            df_c = float(st.slider(
                "Desvio frequência C (Hz)", min_value=-10, max_value=10, value=0, step=1,
                help="Desvio de frequência em Vc. 0 = nominal.", key="df_c"
            ))
            falta_c = st.toggle("Falta de Fase C (Vc = 0)", value=False, key="falta_c")
            if falta_c:
                st.warning("Falta na fase C — correntes muito elevadas.")

        faltas_ativas = sum([falta_a, falta_b, falta_c])
        if faltas_ativas >= 2:
            st.error("Atenção: duas ou mais fases em falta — operação monofásica ou sem tensão. "
                     "Reduza o tempo de simulação.")
        elif faltas_ativas == 1:
            st.warning("Uma fase em falta: operação bifásica — correntes muito elevadas. "
                       "Reduza o tempo de simulação.")

        _tmax_deseq = float(tmax) if tmax > 0.0 else None
        _val_deseq  = min(1.0, float(tmax) - 0.1) if (tmax > 0.0 and tmax <= 1.0) else 1.0
        t_deseq = st.number_input(
            "Instante de início do desequilíbrio (s)",
            min_value=0.0, max_value=_tmax_deseq, value=_val_deseq, step=0.1, format="%.2f",
            help="O desequilíbrio começa a atuar neste instante. Use 0 para aplicar desde o início.",
        )

        any_active = any([deseq_a, deseq_b, deseq_c, falta_a, falta_b, falta_c])
        if any_active and t_deseq > 0.0:
            st.caption(f"Rede balanceada até {t_deseq:.2f} s — desequilíbrio/falta aplicado a partir desse instante.")

        config["deseq_a"]      = deseq_a
        config["deseq_b"]      = deseq_b
        config["deseq_c"]      = deseq_c
        config["falta_fase_a"] = falta_a
        config["falta_fase_b"] = falta_b
        config["falta_fase_c"] = falta_c
        config["t_deseq"]      = t_deseq
        config["df_a"]         = df_a
        config["df_b"]         = df_b
        config["df_c"]         = df_c


def render_broken_bar_ui(config: dict, tmax: float = 2.0, wk: dict | None = None) -> None:
    """Renderiza o expander de Gêmeo Digital — Falha de Barra Quebrada.

    Disponível para qualquer experimento, independente do tipo de partida.
    Preenche config com as chaves:
      broken_bar_severity, t_broken_bar.
    """
    import streamlit as st

    _wk_key   = (wk or {}).get("broken_bar_severity", "wi_broken_bar_severity")
    _t_ref    = float(config.get("t_carga", 0.0))

    # lê valores do session_state ANTES do expander — garante que config é preenchido
    # mesmo quando o expander nunca foi aberto pelo usuário.
    # Usa _wk_key diretamente pois é a key do widget st.slider — o Streamlit
    # sincroniza session_state[key] com o valor atual do widget a cada render.
    broken_bar_severity = float(st.session_state.get(_wk_key, 0.0))
    t_broken_bar        = float(st.session_state.get("wi_broken_bar_t_start", max(0.0, _t_ref)))
    if broken_bar_severity == 0.0:
        t_broken_bar = 0.0
    config["broken_bar_severity"] = broken_bar_severity
    config["t_broken_bar"]        = t_broken_bar

    st.write("")
    with st.expander("Gêmeo Digital — Falha de Barra Quebrada", expanded=False):
        st.info(
            "Simula falha mecânica no rotor por modulação de Rᵣ. "
            "Útil para estudos de MCSA (Motor Current Signature Analysis)."
        )

        with st.expander("O que é falha de barra quebrada? (teoria, MCSA e dicas)", expanded=False):
            st.markdown("""
**Definição.** O rotor de gaiola é formado por **barras condutoras** (alumínio fundido
ou cobre) curto-circuitadas em ambas as extremidades por **anéis de curto-circuito**.
Uma barra **quebrada** (trincada, rompida ou com mau contato no anel) interrompe a
condução de corrente naquele caminho do rotor.

**Causas comuns:**
- Estresse térmico em partidas DOL repetidas (gradiente $\\Delta T > 200\\,°C$ na barra).
- Fadiga mecânica por vibração e ciclos de carga.
- Defeitos de fundição (porosidade no alumínio) ou solda fria nos anéis.
- Corrosão eletroquímica em ambientes agressivos.

**Estatística de campo (IEEE/EPRI):** falhas no rotor representam **8–15%** das falhas
totais em motores de indução, sendo barras quebradas a causa dominante em motores
acima de 100 kW com regime de partidas frequentes.

**Por que a falha gera $(1 \\pm 2s)f_e$?**
Em um rotor saudável, as $N_r$ correntes de barra são senoidais e equilibradas na
frequência de escorregamento $s \\cdot f_e$. Uma barra quebrada cria uma **assimetria
espacial** que gira na velocidade do rotor. Decompondo essa assimetria:

- A componente **direta** induz no estator uma corrente em $f_e(1 - 2s)$ — **banda lateral inferior**.
- A componente **reversa** induz em $f_e(1 + 2s)$ — banda lateral superior.

Estas duas raias laterais, simétricas em torno da fundamental $f_e$, são a **assinatura
espectral clássica** da falha (Thomson & Fenger, 2001).

**Modelo implementado neste simulador:**

$$R_r(t) = R_{r0} \\cdot (1 + \\alpha \\cdot \\cos(2\\theta_{slip}))$$

A modulação a $2\\theta_{slip}$ gera, na corrente de estator, exatamente os pares laterais
$(1 \\pm 2s)f_e$ previstos pela teoria. Aproximação válida para falhas leves a moderadas
($\\alpha \\leq 0{,}3$); falhas severas exigem modelos de barras individuais (não
implementado).

**Severidade $\\alpha$ vs. número de barras quebradas (aproximação empírica):**

| $\\alpha$ | Condição | Amplitude lateral típica (dB) |
|----------|----------|------------------------------|
| 0,00 | Saudável | < −55 |
| 0,05 | Início de fissura, 1 barra parcial | −50 a −45 |
| 0,10 | 1 barra quebrada | −45 a −40 |
| 0,15–0,20 | 2 barras quebradas adjacentes | −40 a −35 |
| 0,30+ | Falha grave, múltiplas barras | > −30 |

A referência é a relação $20 \\log_{10}(I_{lateral}/I_{fundamental})$.

**Critério IEC 60034-26 (gravidade da falha):**

| Banda lateral (dB) | Diagnóstico |
|-------------------|-------------|
| < −50 | Rotor saudável |
| −50 a −45 | Possível fissura, monitorar |
| −45 a −40 | Falha confirmada, planejar manutenção |
| −40 a −35 | Falha avançada, intervenção urgente |
| > −35 | Risco de ruptura do anel, parada imediata |

**Procedimento MCSA (Motor Current Signature Analysis):**
1. Adquira a corrente de uma fase do estator com **alta resolução** ($\\Delta f \\leq 0{,}1$ Hz).
2. Execute **FFT** em janela longa (≥ 10 s) para resolver as raias laterais.
3. Identifique a fundamental $f_e$ e meça as bandas em $f_e(1 \\pm 2s)$.
4. Calcule a amplitude em dB: $20 \\log_{10}(I_{lateral}/I_{fundamental})$.
5. Confronte com o critério IEC 60034-26 acima.

**Dicas para a simulação:**
- Use **partida DOL ou direta com carga** para que o motor atinja regime antes da falha.
- Defina $t_{falha}$ **após o transitório** (≥ 2× o tempo de partida) para isolar a assinatura.
- Aumente $t_{max}$ para **≥ 5 s** para obter resolução espectral suficiente na FFT.
- A análise FFT do simulador exibirá as raias laterais quando $\\alpha > 0$.
- Para visualizar o **torque pulsante**: plote $T_e$ — a oscilação de baixa frequência ($2s \\cdot f_e$, tipicamente 1–5 Hz) é visível mesmo a olho nu.
- Velocidades **muito baixas de escorregamento** ($s < 0{,}5\\%$) afastam as raias laterais demais da fundamental e dificultam a detecção — partir com carga ajuda.

**Limitações do modelo:**
- Assume distribuição senoidal da assimetria — não captura efeitos de barras adjacentes não-uniformes.
- Não modela o **anel de curto-circuito** (cuja falha gera bandas em $(1 \\pm 2s/p)f_e$).
- Saturação magnética e excentricidade dinâmica não são representadas.

**Referências:**
- IEC 60034-26, *Effects of Unbalanced Voltages on the Performance of Three-Phase Cage Induction Motors* (aplica-se também à assinatura de falhas rotóricas).
- Thomson, W. T. & Fenger, M., *Current Signature Analysis to Detect Induction Motor Faults*, IEEE Industry Applications Magazine, vol. 7, no. 4, 2001.
- Nandi, S., Toliyat, H. A. & Li, X., *Condition Monitoring and Fault Diagnosis of Electrical Motors — A Review*, IEEE Trans. on Energy Conversion, vol. 20, no. 4, 2005.
- IEEE Std 1129, *Recommended Practice for Maintenance, Testing, and Replacement of Induction Motors*.
            """)

        st.markdown(
            "Modelo: $R_r(t) = R_{r0} \\cdot (1 + \\alpha \\cdot \\cos(2\\theta_{slip}))$  "
            "para $t \\geq t_{falha}$. "
            "A assinatura espectral exibe componentes laterais em $(1 \\pm 2s)f_e$."
        )
        broken_bar_severity = st.slider(
            "Severidade da falha — $\\alpha$",
            min_value=0.0, max_value=0.5, value=0.0, step=0.01, format="%.2f",
            key=_wk_key,
            help="0 = motor saudável. 0.1 ≈ 1 barra quebrada. 0.3+ = falha grave.",
        )
        if broken_bar_severity > 0:
            _tmax_bb   = float(tmax) if tmax > 0.0 else None
            _val_bb    = max(0.0, _t_ref)
            t_broken_bar = st.number_input(
                "Instante de início da falha — $t_{falha}$ (s)",
                min_value=0.0, max_value=_tmax_bb,
                value=_val_bb, step=0.1, format="%.2f",
                key="wi_broken_bar_t_start",
                help="A modulação de Rᵣ começa neste instante. "
                     "Use um valor após t_carga para simular falha em regime permanente.",
            )
            st.caption(
                f"α = {broken_bar_severity:.2f} — componentes laterais esperados em "
                f"$(1 \\pm 2s)f$ Hz. Use a análise FFT para verificar a assinatura."
            )
            if broken_bar_severity >= 0.3:
                st.warning("Severidade elevada (α ≥ 0.3) — pode causar oscilações visíveis no torque eletromagnético.")
        else:
            t_broken_bar = 0.0
            st.caption("α = 0 — motor saudável. Aumente α para ativar o modelo de falha.")

        # atualiza config com os valores interativos dentro do expander
        config["broken_bar_severity"] = broken_bar_severity
        config["t_broken_bar"]        = t_broken_bar
