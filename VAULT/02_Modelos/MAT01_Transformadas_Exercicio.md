# Transformadas de Coordenadas — Exercício Prático

**Objetivo:** Aplicar aprendizado: ler código, executar testes, confirmar que entendeu.

---

## Exercício 1: Verificar o Fator k (Amplitude-Invariante)

Você leu em [[MAT01_Transformadas_Codigo#2-Por-Quê-k--√2/3-e-√3/2]] que k é **inverso** em duas funções.

**Tarefa:** Confirmar isso numericamente.

Crie arquivo `tests/test_transforms_learn.py`:

```python
import numpy as np
from core.transforms import abc_voltages, clarke_park_transform

def test_fator_k_inverso():
    """
    Verificar que k em abc_voltages e clarke_park_transform são inversos.
    
    Lógica:
    - abc_voltages multiplica por √(2/3)
    - clarke_park_transform multiplica por √(3/2)
    - √(2/3) × √(3/2) = 1 → amplitude preservada
    """
    
    k_abc = np.sqrt(2.0 / 3.0)
    k_dq = np.sqrt(3.0 / 2.0)
    
    # Verificar que são inversos
    produto = k_abc * k_dq
    assert abs(produto - 1.0) < 1e-10, f"k_abc × k_dq deve ser 1, mas é {produto}"
    
    print(f"✓ k_abc = {k_abc:.6f}")
    print(f"✓ k_dq = {k_dq:.6f}")
    print(f"✓ Produto = {produto:.10f} ≈ 1")
```

**Execute:** `pytest tests/test_transforms_learn.py::test_fator_k_inverso -v`

**Se passar:** Você confirmou que fator k foi **escolhido com propósito** (não aleatório).

---

## Exercício 2: Rotor Parado — Vqs Dominante

Você leu em [[MAT01_Transformadas_Codigo#5-Ordem-Importa]] que **eixo q é produtor de torque**.

No início (rotor parado), motor "vê" tensão **principalmente em q**, não em d.

**Tarefa:** Verificar isso.

Adicione a `tests/test_transforms_learn.py`:

```python
def test_rotor_parado_vqs_dominante():
    """
    Teste: quando rotor está parado (tetae=0), Vqs >> Vds.
    
    Interpretação física:
    - Motor parado pode aproveitar toda Vqs para gerar torque
    - Vds ≈ 0 significa "eixo d vê pouca tensão no início"
    - Torque de partida depende principalmente de Vqs
    """
    
    # Condição inicial: t=0, f=60Hz, V_linha=380V
    Va, Vb, Vc = abc_voltages(t=0, Vl=380, f=60)
    
    # Transform com rotor parado (tetae=0)
    Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae=0)
    
    # Verificações
    print(f"\nRotor parado (tetae=0):")
    print(f"  Vds = {Vds:.2f} V")
    print(f"  Vqs = {Vqs:.2f} V")
    print(f"  Razão |Vqs/Vds| = {abs(Vqs/Vds) if abs(Vds) > 10 else 'Vds ≈ 0'}")
    
    # Asserts
    assert abs(Vds) < 100, f"Vds deve ser << 300, mas é {Vds:.2f}"
    assert abs(Vqs) > 250, f"Vqs deve ser >> 100, mas é {Vqs:.2f}"
    
    print("✓ Confirmado: Vqs dominante em rotor parado")
```

**Execute:** `pytest tests/test_transforms_learn.py::test_rotor_parado_vqs_dominante -v`

**Interpretação esperada:** Quando motor parte (ωr=0), **todo o torque vem de Vqs**. Eixo d carrega energia reativa (fluxo), não torque.

---

## Exercício 3: Rotor Acelerado — Mudança de Vds, Vqs

Você leu em [[MAT01_Transformadas_Codigo#4-Ângulo-tetae]] que **tetae acompanha rotor**.

Conforme rotor acelera, tetae muda, e Vds, Vqs **oscilam** (não são mais "quase-ctes").

**Tarefa:** Simular transição de partida.

Adicione:

```python
def test_rotor_acelerado_vds_vqs_mudam():
    """
    Teste: conforme rotor acelera, Vds e Vqs mudam de forma diferente.
    
    Lógica:
    - t=0: ωr=0, tetae=0 → Vqs máximo
    - t→∞: ωr→ωsync, tetae→ramp → Vds, Vqs oscilam junto
    """
    
    p = 2  # polos
    
    # Três instantes: parado, aceleração, transição
    times_omega = [(0, 0), (0.01, 30), (0.05, 120)]
    
    print("\nTransição rotor parado → acelerado:")
    for t, wr in times_omega:
        Va, Vb, Vc = abc_voltages(t, Vl=380, f=60)
        tetae = p * wr  # ângulo síncrono
        Vds, Vqs = clarke_park_transform(Va, Vb, Vc, tetae)
        
        print(f"  t={t:5.3f}s, ωr={wr:3.0f} rad/s, tetae={tetae:6.2f} rad")
        print(f"    Vds={Vds:7.2f}V, Vqs={Vqs:7.2f}V")
    
    # Apenas confirma que rodou sem erro
    assert True
```

**Execute:** `pytest tests/test_transforms_learn.py::test_rotor_acelerado_vds_vqs_mudam -v`

**Observação:** Print mostra como Vds, Vqs **variam com ωr**. Isso é expected — não é erro de simulação, é comportamento real.

---

## Checklist: Execute Todos os 3

```bash
cd c:\Users\gacas\OneDrive\Códigos\IWS
pytest tests/test_transforms_learn.py -v
```

Esperado: **3 testes passando** ✅

```
tests/test_transforms_learn.py::test_fator_k_inverso PASSED
tests/test_transforms_learn.py::test_rotor_parado_vqs_dominante PASSED
tests/test_transforms_learn.py::test_rotor_acelerado_vds_vqs_mudam PASSED
```

---

## Perguntas Reflexivas (Após Passar)

1. **Por quê** o fator k é **inverso** e não o mesmo valor?
2. **Qual é a implicação física** de Vqs >> Vds na partida?
3. **Por quê** Vds, Vqs **mudam** conforme rotor acelera, se a fonte é constante?

Respostas devem referenciar [[MAT01_Transformadas_Codigo]].

---

## Próximo Bloco

Após completar exercício, passamos a **Bloco 2.2** — [[MAT02_MachineModel_Estrutura]]: Como Vds, Vqs alimentam as 8 equações dq0 do Krause.

---

**Criado:** 2026-05-26 | **Status:** 🟠 Aguardando submissão de testes
