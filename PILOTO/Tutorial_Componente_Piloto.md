# Como Construir um Componente de Simulação de Motor — Do Zero

> **Para quem é este tutorial?**
> Para alguém com **zero experiência em programação**. Cada seção parte de um problema concreto, apresenta a ferramenta Python que resolve aquele problema específico, explica por que ela funciona, e só então mostra o código. Ao final você terá construído, decisão por decisão, um simulador de torque interativo — e saberá *por que* cada parte existe.

---

## Como usar este tutorial

Leia na ordem. Não pule seções. Cada passo resolve um problema novo que surgiu do passo anterior.

> [!tip] Regra de ouro
> Antes de qualquer bloco de código, leia o problema que ele resolve. Código sem problema é só sintaxe — não ensina nada.

---

## Índice

1. [[#Parte 1 — Ambiente]]
2. [[#Parte 2 — O primeiro problema: guardar um número]]
3. [[#Parte 3 — O segundo problema: calcular com esses números]]
4. [[#Parte 4 — O terceiro problema: não repetir o mesmo cálculo]]
5. [[#Parte 5 — A física que vamos programar]]
6. [[#Parte 6 — Traduzindo a física para código]]
7. [[#Parte 7 — O quarto problema: calcular para muitos valores]]
8. [[#Parte 8 — O quinto problema: o usuário precisa digitar os parâmetros]]
9. [[#Parte 9 — O sexto problema: a interface de terminal é horrível]]
10. [[#Parte 10 — Como o Streamlit monta uma página]]
11. [[#Parte 11 — Construindo a interface visual passo a passo]]
12. [[#Parte 12 — Código completo consolidado]]
13. [[#Parte 13 — Como salvar e organizar a pasta PILOTO]]

---

## Parte 1 — Ambiente

### O problema

Para executar qualquer código Python, você precisa de dois programas instalados: o **Python** (a linguagem) e um editor de texto para escrever os arquivos.

### O que instalar

**Python** — a linguagem. Gratuita, roda em qualquer sistema.

Acesse `python.org/downloads`, baixe a versão mais recente. Durante a instalação no Windows, **marque obrigatoriamente a opção "Add Python to PATH"** — sem isso, o terminal não encontra o Python.

**VS Code** — editor de texto com suporte a Python. Opcional, mas recomendado.

Acesse `code.visualstudio.com` e instale.

### Verificando que funcionou

Abra o terminal. No Windows: pressione `Win + R`, digite `cmd`, pressione Enter.

Digite:

```
python --version
```

Se aparecer algo como `Python 3.12.0` — está correto.

### Instalando o Streamlit

Ainda no terminal:

```
pip install streamlit numpy pandas
```

`pip` é o gerenciador de pacotes do Python — ele baixa e instala bibliotecas adicionais. `streamlit`, `numpy` e `pandas` são bibliotecas que vamos usar no tutorial.

Aguarde o download terminar. Para verificar:

```
streamlit --version
```

Se aparecer um número de versão — pronto.

> [!success] Ambiente pronto
> Python, Streamlit, NumPy e Pandas instalados. Podemos começar a programar.

---

## Parte 2 — O primeiro problema: guardar um número

### O problema

Queremos calcular o torque de um motor. Para isso precisamos de dados: tensão, frequência, resistências, reatâncias.

Esses valores precisam ficar guardados em algum lugar enquanto o programa roda — de forma que possamos referenciá-los pelo nome depois, em vez de digitar o número toda vez.

### A solução: variáveis

Em Python, **variável** é um nome que aponta para um valor guardado na memória. É como uma etiqueta colada numa caixa: a etiqueta é o nome, o conteúdo da caixa é o valor.

Para criar uma variável, usamos o operador `=` (lê-se: "recebe"):

```python
tensao_linha = 380.0
```

Isso diz ao Python: *"crie uma caixa chamada `tensao_linha` e guarde o valor `380.0` dentro dela"*.

A partir dessa linha, sempre que o programa encontrar o nome `tensao_linha`, ele vai buscar `380.0` da memória.

### Por que `.0` depois do número?

`380` (sem ponto) é um **inteiro** — um número sem casas decimais.
`380.0` (com ponto) é um **float** — um número com casas decimais.

Em engenharia, quase sempre queremos floats: resistências, tensões, ângulos raramente são inteiros exatos. O ponto decimal sinaliza ao Python que o número pode ter casas decimais.

> [!warning] Ponto, não vírgula
> Python usa ponto como separador decimal (`380.5`), nunca vírgula (`380,5`). Vírgula tem outro significado na linguagem.

### Criando o arquivo

Crie uma pasta chamada `PILOTO` em qualquer local do seu computador.

Dentro dela, crie um arquivo chamado `calculador_torque.py` (no VS Code: Arquivo → Novo Arquivo → salve com esse nome).

Digite:

```python
# Parâmetros do motor
tensao_linha = 380.0
frequencia   = 60.0
num_polos    = 4
```

> [!tip] O símbolo `#`
> Linhas que começam com `#` são **comentários** — o Python as ignora completamente. Servem para explicar o código para humanos. Use-os para registrar o que cada variável representa.

`num_polos = 4` sem ponto decimal — número de polos é sempre inteiro.

O programa ainda não *faz* nada visível. Ele apenas guarda três valores na memória. Isso está correto — estamos construindo peça por peça.

---

## Parte 3 — O segundo problema: calcular com esses números

> [!info] Funções e módulos introduzidos nesta parte
>
> | Função / símbolo | O que faz | Como usar |
> |---|---|---|
> | `+` `-` `*` `/` `**` | Operações aritméticas básicas | `resultado = a * b` |
> | `print(valor)` | Exibe um valor no terminal | `print("Tensão:", tensao, "V")` |
> | `import math` | Carrega o módulo de funções matemáticas | Escrever no topo do arquivo |
> | `math.sqrt(x)` | Raiz quadrada de x | `math.sqrt(3)` → `1.732` |
> | `math.pi` | Constante π (3.14159…) | `2 * math.pi * f` |
> | `round(valor, n)` | Arredonda para n casas decimais | `round(219.393, 2)` → `219.39` |

### O problema

Guardamos os valores. Agora precisamos usá-los em cálculos. E precisamos ver os resultados.

### Operadores matemáticos em Python

Python entende matemática diretamente:

| Operação | Símbolo | Exemplo |
|---|---|---|
| Adição | `+` | `3 + 2` → `5` |
| Subtração | `-` | `3 - 2` → `1` |
| Multiplicação | `*` | `3 * 2` → `6` |
| Divisão | `/` | `3 / 2` → `1.5` |
| Potência (elevado a) | `**` | `3 ** 2` → `9` |

Quando você usa o nome de uma variável numa operação, Python substitui pelo valor guardado:

```python
tensao_linha = 380.0
corrente = 10.0
potencia = tensao_linha * corrente   # Python calcula 380.0 * 10.0 = 3800.0
```

### Como ver o resultado: a função `print()`

Sem `print()`, o Python executa os cálculos mas não mostra nada. `print()` exibe o valor no terminal.

```python
print(potencia)
```

Saída no terminal:
```
3800.0
```

Você também pode combinar texto e número:

```python
print("Potência:", potencia, "W")
```

Saída:
```
Potência: 3800.0 W
```

### Precisamos da raiz quadrada — problema

A fórmula do torque usa raiz quadrada ($\sqrt{x}$). Python puro não tem raiz quadrada diretamente — ela está no módulo `math`.

**Módulo** é um arquivo de funções extras que o Python não carrega automaticamente (para não ocupar memória com coisas que talvez você não vá usar). Para carregar um módulo, usamos `import`:

```python
import math
```

Com isso, a função `math.sqrt()` fica disponível:

```python
import math
raiz = math.sqrt(9.0)   # resultado: 3.0
```

A notação `math.sqrt` significa: *"a função `sqrt` que está dentro do módulo `math`"*.

### Adicionando ao arquivo

Abra `calculador_torque.py` e adicione abaixo do que já foi escrito:

```python
import math

# Tensão de fase (tensão de linha dividida por raiz de 3)
tensao_fase = tensao_linha / math.sqrt(3)
print("Tensão de fase:", round(tensao_fase, 2), "V")
```

> [!tip] `round(valor, casas)`
> Arredonda um número para o número de casas decimais indicado. `round(219.39340, 2)` → `219.39`. Usado aqui só para exibição limpa — o valor completo continua guardado em `tensao_fase`.

Execute no terminal (dentro da pasta `PILOTO`):

```
python calculador_torque.py
```

Saída esperada:
```
Tensão de fase: 219.39 V
```

**Pausa e reflexão:** acabamos de fazer o primeiro cálculo real de engenharia — convertemos tensão de linha para tensão de fase. O programa leu `380.0`, dividiu por √3, e exibiu o resultado. Isso é o núcleo do que um simulador faz.

---

## Parte 4 — O terceiro problema: não repetir o mesmo cálculo

> [!info] Conceitos introduzidos nesta parte
>
> | Conceito / sintaxe | O que faz | Como usar |
> |---|---|---|
> | `def nome(param):` | Define uma função com nome e parâmetros | `def calcular(a, b):` |
> | `return valor` | Devolve um resultado da função para quem a chamou | `return a + b` |
> | `return a, b, c` | Devolve múltiplos valores como tupla (grupo ordenado) | `return Vth, Rth, Xth` |
> | `x, y, z = funcao()` | Desempacota tupla: distribui cada valor para sua variável na ordem | `Vth, Rth, Xth = calcular_thevenin(...)` |
> | `import modulo as alias` | Importa um arquivo `.py` como módulo com apelido | `import motor_functions as mf` |
> | `mf.funcao(args)` | Chama uma função do módulo importado | `mf.calcular_tensao_fase(380.0)` |

### O problema

No simulador completo, vamos precisar calcular a tensão de fase em vários lugares diferentes — ao mudar parâmetros, ao recalcular para escorregamentos diferentes, ao exibir resultados.

Se escrevermos `tensao_linha / math.sqrt(3)` toda vez, e depois descobrirmos que a fórmula estava errada (ou que precisamos de uma versão diferente), precisaríamos corrigir em *todos* os lugares.

Existe uma solução: encapsular o cálculo num bloco com nome próprio, que pode ser chamado quantas vezes quiser. Esse bloco é chamado de **função**.

### O que é uma função

Função é um bloco de código com:
- **Nome** — para identificá-la
- **Parâmetros** — os dados que ela precisa receber para trabalhar
- **Corpo** — as instruções que executa
- **Retorno** — o resultado que ela entrega de volta

Pense numa calculadora científica: ela tem uma tecla `√`. Quando você pressiona essa tecla passando um número, ela executa internamente a operação de raiz e devolve o resultado. Você não precisa saber *como* ela calcula internamente — só precisa saber o que dar pra ela e o que esperar de volta.

Uma função Python é exatamente isso: uma "tecla" que você define, com o nome que quiser.

### A sintaxe de definição

```python
def nome_da_funcao(parametro1, parametro2):
    resultado = parametro1 / parametro2
    return resultado
```

Dissecando linha por linha:

**`def`** — palavra-chave que inicia a definição de uma função. "def" vem de *define*.

**`nome_da_funcao`** — você escolhe. Deve ser descritivo. Use underscore `_` para separar palavras (convenção Python). Evite acentos em nomes de funções.

**`(parametro1, parametro2)`** — lista de "ingredientes" que a função precisa receber. Esses nomes só existem *dentro* da função — são como variáveis locais.

**`:`** — obrigatório. Indica que o bloco da função começa na linha seguinte.

**Indentação** — as linhas do corpo da função são recuadas com 4 espaços (ou 1 Tab). Em Python, a indentação define o que está dentro da função. Sem indentação correta, Python dá erro.

**`return`** — entrega o valor calculado de volta para quem chamou a função.

### Como usar (chamar) uma função

Depois de definir, você usa o nome da função seguido de parênteses com os valores:

```python
def dividir(a, b):
    return a / b

x = dividir(380.0, 1.732)
print(x)
```

Saída: `219.27...`

O que aconteceu:
1. Python encontrou `dividir(380.0, 1.732)`
2. Entrou na função, atribuiu `a = 380.0` e `b = 1.732`
3. Calculou `a / b` = `219.27...`
4. `return` devolveu esse valor
5. `x` recebeu o valor devolvido

### Retornando múltiplos valores: tuplas

**Problema novo:** às vezes uma função precisa calcular e devolver *vários* resultados — não apenas um.

Por exemplo: a função que calcula o Equivalente de Thevenin (que veremos mais adiante) precisa calcular três valores: $V_{th}$, $R_{th}$ e $X_{th}$. Como devolver os três de uma única função?

**Solução:** `return` aceita múltiplos valores separados por vírgula. Eles são entregues como uma **tupla** — um grupo ordenado de valores.

```python
def calcular_dois_coisas(a, b):
    resultado1 = a + b
    resultado2 = a * b
    return resultado1, resultado2
```

Quando você chama essa função e atribui a múltiplas variáveis, Python **desempacota** os valores:

```python
soma, produto = calcular_dois_coisas(3, 5)
print(soma)      # 8
print(produto)   # 15
```

O que aconteceu:
1. A função retornou `(8, 15)` — uma tupla com dois valores
2. Python viu `a, b =` (duas variáveis à esquerda) e distribuiu: `a = 8`, `b = 15`
3. Cada variável recebeu um valor na ordem

Pode haver quantos valores quiser:

```python
def calcular_tres(a):
    return a, a*2, a*3

x, y, z = calcular_tres(5)
print(x, y, z)   # 5 10 15
```

> [!note] Conceito fixado
> Múltiplos `return` com vírgula produzem uma tupla. Múltiplas variáveis à esquerda de `=` desempacotam essa tupla, distribuindo cada valor para sua variável correspondente.

### Criando a função de tensão de fase

Crie um novo arquivo na pasta `PILOTO` chamado `motor_functions.py`.

Digite:

```python
import math


def calcular_tensao_fase(tensao_linha):
    tensao_fase = tensao_linha / math.sqrt(3)
    return tensao_fase
```

Agora modifique `calculador_torque.py` para usar esse arquivo:

```python
import motor_functions as mf

tensao_linha = 380.0
tensao_fase = mf.calcular_tensao_fase(tensao_linha)
print("Tensão de fase:", round(tensao_fase, 2), "V")
```

> [!tip] `import motor_functions as mf`
> Importamos o arquivo `motor_functions.py` como um módulo. O `as mf` cria um apelido curto — assim escrevemos `mf.calcular_tensao_fase(...)` em vez de `motor_functions.calcular_tensao_fase(...)`.
>
> Os dois arquivos precisam estar na **mesma pasta** para isso funcionar.

Execute novamente:
```
python calculador_torque.py
```

Mesmo resultado de antes — mas agora o cálculo está isolado em sua própria função, com nome descritivo, reutilizável.

**Por que isso importa:** `calculador_torque.py` não precisa mais saber *como* a tensão de fase é calculada. Só precisa saber que existe uma função que faz isso. Essa separação de responsabilidades é o núcleo da organização de qualquer software real.

---

## Parte 5 — A física que vamos programar

Antes de continuar programando, precisamos entender o que vamos calcular. Programar sem entender a física é seguir uma receita sem saber o que está cozinhando.

### O motor de indução trifásico

O motor que vamos simular é o mais comum na indústria: o **motor de indução trifásico de gaiola de esquilo**.

Funcionamento simplificado:
1. Corrente elétrica nas bobinas do **estator** (parte parada) gera um campo magnético girante
2. Esse campo induz correntes no **rotor** (parte que gira)
3. A interação entre os campos produz o **torque** — a força que faz o eixo girar

### O escorregamento — por que o rotor não acompanha o campo

O campo magnético gira a uma velocidade chamada **velocidade síncrona** ($n_s$). O rotor gira um pouco mais devagar — se girasse na mesma velocidade, não haveria variação de campo, não haveria corrente induzida, não haveria torque.

Essa diferença relativa de velocidade é o **escorregamento** $s$:

$$s = \frac{n_s - n_r}{n_s}$$

- $s = 0$: rotor na velocidade do campo → sem torque (motor em vazio ideal)
- $s = 1$: rotor parado → partida (maior corrente, torque de partida)
- $s = 0.05$: escorregamento de 5% → operação normal com carga

### A velocidade síncrona

A velocidade do campo magnético depende da frequência da rede e do número de polos do motor:

$$\omega_s = \frac{2\pi \cdot f}{p/2} \quad [\text{rad/s}]$$

- $f$ = frequência da rede [Hz] (60 Hz no Brasil)
- $p$ = número de polos

> [!info] Por que dividir por p/2?
> Os $p$ polos formam $p/2$ **pares** de polos. A velocidade do campo depende do número de pares, não do total de polos. Um motor de 4 polos tem 2 pares → campo gira a $\frac{2\pi \times 60}{2} = 188{,}5$ rad/s = 1800 RPM.

### O circuito equivalente monofásico

Para calcular o torque matematicamente, representamos o motor por um **circuito elétrico equivalente** — uma simplificação que captura o comportamento essencial.

Os parâmetros desse circuito são:

| Símbolo | Nome | Unidade |
|---|---|---|
| $R_s$ | Resistência do estator | Ω |
| $X_s$ | Reatância de dispersão do estator | Ω |
| $X_m$ | Reatância de magnetização | Ω |
| $R_r$ | Resistência do rotor (referida ao estator) | Ω |
| $X_r$ | Reatância de dispersão do rotor | Ω |

### O Equivalente de Thevenin

Para simplificar os cálculos, substituímos a parte do estator + magnetização por um equivalente mais simples chamado **Equivalente de Thevenin**:

$$V_{th} = V_\phi \cdot \frac{X_m}{\sqrt{R_s^2 + (X_s + X_m)^2}}$$

$$R_{th} = R_s \cdot \left(\frac{X_m}{X_s + X_m}\right)^2$$

$$X_{th} = \frac{X_s \cdot X_m}{X_s + X_m}$$

Onde $V_\phi$ é a tensão de fase.

### A equação do torque

Com o Equivalente de Thevenin calculado, o torque eletromagnético para um dado escorregamento $s$ é:

$$T_e = \frac{3}{\omega_s} \cdot \frac{V_{th}^2 \cdot R_r / s}{(R_{th} + R_r/s)^2 + (X_{th} + X_r)^2}$$

Esta é a equação que vamos transformar em código Python nas próximas seções.

> [!note] Conceitos fixados
> Temos os parâmetros, as equações e a física. Próximo passo: traduzir cada equação em uma função Python.

---

## Parte 6 — Traduzindo a física para código

### O plano

Vamos criar uma função Python para cada equação da Parte 5. A ordem importa — cada cálculo depende do anterior:

```
tensao_fase  →  thevenin  →  torque
omega_s      ↗
```

Faremos isso em passos, adicionando uma função de cada vez ao arquivo `motor_functions.py` e testando imediatamente.

---

### Passo 6.1 — Velocidade síncrona

**O que precisamos calcular:**
$$\omega_s = \frac{2\pi \cdot f}{p/2}$$

**Traduzindo para Python:** `math.pi` é o valor de π. O resto são operações aritméticas simples.

Adicione ao final de `motor_functions.py`:

```python
def calcular_omega_sincrona(frequencia, num_polos):
    omega_s = (2 * math.pi * frequencia) / (num_polos / 2)
    return omega_s
```

Teste em `calculador_torque.py` — adicione ao final:

```python
frequencia = 60.0
num_polos  = 4

omega_s = mf.calcular_omega_sincrona(frequencia, num_polos)
print("Velocidade síncrona:", round(omega_s, 2), "rad/s")
```

Execute. Saída esperada:
```
Velocidade síncrona: 188.5 rad/s
```

> [!info] Verificação física
> 188,5 rad/s = 1800 RPM. Motor de 4 polos, rede 60 Hz → campo gira a 1800 RPM. Correto.

---

### Passo 6.2 — Equivalente de Thevenin

**O que precisamos calcular** (as três equações juntas):
$$V_{th} = V_\phi \cdot \frac{X_m}{\sqrt{R_s^2 + (X_s + X_m)^2}}$$
$$R_{th} = R_s \cdot \left(\frac{X_m}{X_s + X_m}\right)^2$$
$$X_{th} = \frac{X_s \cdot X_m}{X_s + X_m}$$

**O que precisamos fazer:** Thevenin calcula três valores ($V_{th}$, $R_{th}$, $X_{th}$). Já aprendemos em Parte 4 como retornar múltiplos valores com tuplas e desempacotamento.

Adicione ao final de `motor_functions.py`:

```python
def calcular_thevenin(tensao_fase, Rs, Xs, Xm):
    Vth = tensao_fase * (Xm / math.sqrt(Rs**2 + (Xs + Xm)**2))
    Rth = Rs * (Xm / (Xs + Xm))**2
    Xth = (Xs * Xm) / (Xs + Xm)
    return Vth, Rth, Xth
```

Adicione ao `calculador_torque.py`:

```python
Rs = 0.641
Xs = 1.106
Xm = 26.3

Vth, Rth, Xth = mf.calcular_thevenin(tensao_fase, Rs, Xs, Xm)
print("Vth:", round(Vth, 2), "V")
print("Rth:", round(Rth, 4), "Ohm")
print("Xth:", round(Xth, 4), "Ohm")
```

Execute. Saída esperada:
```
Vth: 217.69 V
Rth: 0.5905 Ohm
Xth: 1.0615 Ohm
```

---

### Passo 6.3 — O torque

**O que precisamos calcular:**
$$T_e = \frac{3}{\omega_s} \cdot \frac{V_{th}^2 \cdot R_r / s}{(R_{th} + R_r/s)^2 + (X_{th} + X_r)^2}$$

**Estratégia de tradução:** a fórmula é longa. Dividir em `numerador` e `denominador` torna o código legível e fácil de depurar.

Adicione ao final de `motor_functions.py`:

```python
def calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s):
    numerador   = 3 * Vth**2 * (Rr / s)
    denominador = omega_s * ((Rth + Rr/s)**2 + (Xth + Xr)**2)
    return numerador / denominador
```

Adicione ao `calculador_torque.py`:

```python
Rr = 0.332
Xr = 0.464

escorregamento = 0.05
Te = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, escorregamento)
print("Torque para s=0.05:", round(Te, 2), "N.m")
```

Execute. Saída esperada:
```
Torque para s=0.05: 45.83 N.m
```

**Pausa:** acabamos de calcular o torque eletromagnético de um motor de indução a partir dos parâmetros do circuito equivalente. Cada função faz exatamente uma coisa. Cada resultado foi verificado passo a passo.

---

## Parte 7 — O quarto problema: calcular para muitos valores

> [!info] Funções e estruturas introduzidas nesta parte
>
> | Função / estrutura | O que faz | Como usar |
> |---|---|---|
> | `for x in sequencia:` | Executa o bloco indentado uma vez para cada item da sequência | `for s in escorregamentos:` |
> | `import numpy as np` | Carrega a biblioteca NumPy (computação numérica) | Escrever no topo do arquivo |
> | `np.linspace(a, b, n)` | Gera n valores igualmente espaçados entre a e b | `np.linspace(0.001, 1.0, 200)` |
> | `lista = []` | Cria uma lista vazia | `torques = []` |
> | `lista.append(valor)` | Adiciona um valor ao final da lista | `torques.append(Te)` |
> | `lista[i]` | Acessa o elemento de índice i (começa em 0) | `torques[0]` → primeiro elemento |
> | `lista[-1]` | Acessa o último elemento da lista | `torques[-1]` → último torque |
> | `f"texto {variavel:.2f}"` | f-string: insere variável dentro de texto com formatação | `f"Te={Te:.2f} N.m"` |

### O problema

Calculamos o torque para um único escorregamento (s=0.05). Mas o que realmente interessa é a **curva de torque** — como o torque varia desde a partida (s=1) até regime permanente (s≈0).

Precisamos calcular para centenas de valores de escorregamento. Escrever `calcular_torque(...)` cem vezes é inviável.

### A solução: laço de repetição `for`

Um laço `for` executa um bloco de código várias vezes, uma para cada item de uma sequência.

**Problema menor primeiro:** como funciona o `for`?

```python
for numero in [1, 2, 3, 4, 5]:
    print(numero)
```

Saída:
```
1
2
3
4
5
```

Python pega cada valor da lista `[1, 2, 3, 4, 5]`, guarda em `numero`, executa o bloco indentado, e passa pro próximo. O bloco indentado é executado tantas vezes quantos forem os itens da lista.

### Gerando uma sequência de floats: `np.linspace()`

Para a curva de torque, precisamos de uma sequência de números decimais (escorregamentos de 0.001 a 1.0). Listas Python manuais não servem para isso. Usamos o **NumPy**.

NumPy é uma biblioteca para computação numérica. A função `np.linspace(início, fim, n)` gera `n` valores igualmente espaçados:

```python
import numpy as np

valores = np.linspace(0.0, 1.0, 5)
# resultado: [0.0, 0.25, 0.5, 0.75, 1.0]
```

### Guardando resultados: a lista

Para guardar o torque de cada escorregamento, precisamos de uma **lista** — uma sequência de valores que cresce ao longo do loop.

```python
torques = []                          # cria lista vazia
for s in np.linspace(0.001, 1.0, 5):
    Te = mf.calcular_torque(...)
    torques.append(Te)                # adiciona o valor ao final da lista
```

`torques.append(valor)` adiciona `valor` ao final da lista `torques`.

### Adicionando ao calculador

Adicione ao final de `calculador_torque.py`:

```python
import numpy as np

escorregamentos = np.linspace(0.001, 1.0, 20)
torques = []

for s in escorregamentos:
    Te = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s)
    torques.append(Te)

print("\n--- Curva de Torque ---")
for i in range(len(escorregamentos)):
    print(f"s={escorregamentos[i]:.3f}  Te={torques[i]:.2f} N.m")
```

> [!tip] f-strings
> `f"s={escorregamentos[i]:.3f}"` — o `f` antes das aspas indica uma **f-string**. Dentro de `{}` vai qualquer expressão Python, que é substituída pelo valor. O `:.3f` formata como float com 3 casas decimais.

Execute. Você verá 20 linhas com escorregamento e torque correspondente.

**O que acabamos de fazer:** calculamos a curva de torque completa do motor. Esse é o dado central de qualquer simulador de partida de motor.

---

## Parte 8 — O quinto problema: o usuário precisa digitar os parâmetros

> [!info] Funções introduzidas nesta parte
>
> | Função | O que faz | Como usar |
> |---|---|---|
> | `input("mensagem")` | Pausa o programa, exibe a mensagem e aguarda o usuário digitar. Devolve **texto**. | `nome = input("Digite: ")` |
> | `float(texto)` | Converte texto para número decimal | `float("380")` → `380.0` |
> | `int(texto)` | Converte texto para número inteiro | `int("4")` → `4` |

> [!warning] Atenção
> `input()` **sempre** devolve texto (`str`), mesmo que o usuário digite um número. Sem `float()` ou `int()`, operações matemáticas com o valor retornado causam erro.

### O problema

Até agora os parâmetros estão fixos no código. Para ser útil como simulador, o programa precisa aceitar parâmetros diferentes sem que o usuário precise editar o arquivo `.py`.

### A solução: `input()`

`input("mensagem")` pausa o programa, exibe a mensagem, espera o usuário digitar algo e pressionar Enter, e devolve o que foi digitado como **texto**.

```python
nome = input("Digite seu nome: ")
print("Olá,", nome)
```

Quando executado, o programa exibe `Digite seu nome: ` e aguarda. Se o usuário digitar `Maria` e pressionar Enter, `nome` recebe `"Maria"`.

### Problema dentro do problema: `input()` devolve texto, não número

Se o usuário digitar `380`, `input()` devolve a string `"380"` — texto, não número. Não dá para fazer aritmética com texto:

```python
tensao = input("Tensão: ")
tensao * 2    # erro! não dá para multiplicar texto por 2
```

**Solução:** converter com `float()`:

```python
tensao = float(input("Tensão de linha (V): "))
```

O que acontece:
1. `input(...)` recebe `"380"` (texto)
2. `float("380")` converte para `380.0` (número)
3. `tensao` recebe `380.0`

### Testando a entrada

Crie um arquivo separado `entrada_teste.py` na pasta `PILOTO` para testar isso isoladamente:

```python
tensao_linha = float(input("Tensão de linha (V) [ex: 380]: "))
frequencia   = float(input("Frequência (Hz) [ex: 60]: "))
num_polos    = int(input("Número de polos [ex: 4]: "))

print(f"Tensão: {tensao_linha} V, Frequência: {frequencia} Hz, Polos: {num_polos}")
```

> [!tip] `int()` vs `float()`
> `int()` converte para número inteiro. Número de polos é sempre inteiro, então usamos `int()` em vez de `float()`.

Execute:
```
python entrada_teste.py
```

O programa pede os três valores, um por um, e exibe o resultado.

### Conclusão desta etapa

`input()` funciona para testes rápidos, mas é péssima para um simulador real: o usuário precisa digitar tudo de novo toda vez, não dá para ver as entradas e saídas ao mesmo tempo, e qualquer erro de digitação trava o programa.

Isso nos leva ao próximo problema.

---

## Parte 9 — O sexto problema: a interface de terminal é horrível

> [!info] Funções Streamlit introduzidas nesta parte
>
> | Função | O que faz | Como usar |
> |---|---|---|
> | `import streamlit as st` | Carrega a biblioteca Streamlit | Escrever no topo do arquivo |
> | `st.set_page_config(...)` | Configura título da aba e layout da página. Deve ser o **primeiro** comando `st.` do arquivo. | `st.set_page_config(page_title="App", layout="wide")` |
> | `st.title("texto")` | Exibe um título grande no topo da página | `st.title("Simulador")` |
> | `st.markdown("texto")` | Exibe texto com formatação Markdown | `st.markdown("**negrito**")` |
> | `st.write(valor)` | Exibe qualquer valor (texto, número, tabela) | `st.write("Tensão:", tensao)` |
> | `st.number_input("rótulo", value=X)` | Campo numérico editável. Devolve o número atual como float. | `tensao = st.number_input("V", value=380.0)` |

### O problema

Um simulador de engenharia precisa de:
- Campos visuais para digitar parâmetros
- Sliders para explorar valores
- Gráficos dos resultados
- Atualização instantânea quando algo muda

O terminal não oferece nada disso.

### A solução: Streamlit

**Streamlit** é uma biblioteca Python que converte código em uma interface web interativa no navegador — sem precisar aprender HTML, CSS ou JavaScript.

A lógica do Streamlit é simples:
1. Você escreve um arquivo `.py` normal
2. O Streamlit lê esse arquivo de cima para baixo
3. Cada comando `st.algo()` vira um elemento visual na página
4. Quando o usuário interage com qualquer elemento, o Streamlit **re-executa o arquivo inteiro** do zero
5. Os resultados são recalculados automaticamente com os novos valores

### O primeiro elemento: `st.title()`

Para entender o Streamlit, vamos criar uma página mínima.

Crie `app_piloto.py` na pasta `PILOTO`:

```python
import streamlit as st

st.title("Meu primeiro app")
st.write("Olá, mundo.")
```

Execute no terminal:
```
streamlit run app_piloto.py
```

O Streamlit abrirá automaticamente uma aba no navegador com o título e o texto. Isso é um app Streamlit funcional — duas linhas.

**Por que funciona:** `st.title()` gera um título HTML grande. `st.write()` gera um parágrafo. O Streamlit cuida de todo o HTML/CSS por baixo.

### O elemento de entrada: `st.number_input()`

Para substituir o `input()` do terminal, usamos `st.number_input()`:

```python
tensao_linha = st.number_input(
    "Tensão de linha (V)",
    value=380.0
)
```

Isso cria um campo numérico na página com o rótulo `"Tensão de linha (V)"` e valor padrão `380.0`. O que o usuário digitar nesse campo é devolvido pela função e guardado em `tensao_linha`.

**Diferença crucial em relação ao `input()`:** o valor já vem como número (não precisa de `float()`), tem valor padrão, e atualiza automaticamente.

Teste adicionando ao `app_piloto.py`:

```python
import streamlit as st

st.title("Meu primeiro app")

tensao_linha = st.number_input("Tensão de linha (V)", value=380.0)
st.write("Você digitou:", tensao_linha, "V")
```

Execute e mude o valor no campo — o texto abaixo atualiza instantaneamente, sem precisar clicar em nenhum botão.

Agora entendemos as ferramentas. Mas antes de sair adicionando elementos, precisamos entender **como o Streamlit organiza o espaço visual da página**. Esse modelo mental é o que separa uma interface que "funciona" de uma que faz sentido para o usuário.

---

## Parte 10 — Como o Streamlit monta uma página

> [!info] Funções de layout introduzidas nesta parte
>
> | Função | O que faz | Como usar |
> |---|---|---|
> | `st.sidebar.qualquer_coisa()` | Coloca o elemento na barra lateral em vez do conteúdo principal | `st.sidebar.number_input(...)` |
> | `st.sidebar.header("texto")` | Título na barra lateral | `st.sidebar.header("Parâmetros")` |
> | `st.sidebar.subheader("texto")` | Subtítulo na barra lateral | `st.sidebar.subheader("Circuito")` |
> | `col_a, col_b = st.columns([2, 1])` | Divide o conteúdo principal em colunas com proporções definidas | `col_esq, col_dir = st.columns([2, 1])` |
> | `with coluna:` | Direciona os elementos indentados abaixo para aquela coluna | `with col_esq: st.write(...)` |
> | `st.subheader("texto")` | Subtítulo no conteúdo principal | `st.subheader("Curva de Torque")` |
> | `st.divider()` | Linha horizontal separadora | `st.divider()` |

### O problema

Se você simplesmente empilhar `st.number_input()`, `st.line_chart()`, `st.metric()` um após o outro, tudo vai aparecer numa única coluna vertical, de cima para baixo. Isso funciona para um script simples, mas para um simulador é ruim: o usuário precisa rolar a página para ver parâmetros e resultados ao mesmo tempo.

Precisamos entender as **zonas de layout** do Streamlit para posicionar cada elemento onde faz sentido.

### As três zonas da página Streamlit

Uma página Streamlit tem três regiões onde você pode colocar elementos:

```
┌─────────────────────────────────────────────────────────┐
│                      TOPO DA PÁGINA                      │
│  st.title(), st.markdown(), st.header() — sempre aqui   │
├──────────────┬──────────────────────────────────────────┤
│   SIDEBAR    │           CONTEÚDO PRINCIPAL             │
│              │                                          │
│  Parâmetros  │  Gráficos, tabelas, métricas, resultados │
│  de entrada  │                                          │
│              │                                          │
│ st.sidebar   │  st.write(), st.line_chart(),            │
│ .number_     │  st.columns(), st.metric(), etc.         │
│  input()     │                                          │
│  .selectbox  │                                          │
│  .slider()   │                                          │
│  etc.        │                                          │
└──────────────┴──────────────────────────────────────────┘
```

**Sidebar (barra lateral):** aparece à esquerda, sempre visível. Ideal para parâmetros de configuração — coisas que o usuário ajusta mas que não precisam de destaque visual.

**Conteúdo principal:** o resto da página. É onde vão os resultados: gráficos, tabelas, métricas.

**Regra prática:** entrada vai na sidebar, saída vai no conteúdo principal.

### Como colocar algo na sidebar

Todo elemento Streamlit que começa com `st.sidebar.` vai para a barra lateral:

```python
# Isso aparece na barra lateral:
tensao = st.sidebar.number_input("Tensão (V)", value=380.0)

# Isso aparece no conteúdo principal:
st.write("Tensão:", tensao)
```

Se você não usar `st.sidebar.`, o elemento vai para o conteúdo principal, empilhado verticalmente.

### O problema do conteúdo principal: tudo numa coluna só

Por padrão, o conteúdo principal é uma única coluna. Se você colocar um gráfico e depois as métricas:

```python
st.line_chart(...)   # gráfico ocupa toda a largura
st.metric(...)       # métrica aparece abaixo, não ao lado
```

Para colocar elementos lado a lado, precisamos dividir o espaço em **colunas**.

### Dividindo o espaço em colunas: `st.columns()`

`st.columns(n)` divide o conteúdo principal em `n` colunas e devolve uma lista de objetos, um por coluna:

```python
col_esq, col_dir = st.columns(2)   # duas colunas de largura igual
```

Para definir proporções diferentes, passe uma lista com os pesos relativos:

```python
col_esq, col_dir = st.columns([2, 1])
# col_esq ocupa 2/3 da largura
# col_dir ocupa 1/3 da largura
```

Para colocar elementos *dentro* de uma coluna específica, use o bloco `with`:

```python
col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.write("Isso aparece na coluna esquerda")
    st.line_chart(...)

with col_dir:
    st.write("Isso aparece na coluna direita")
    st.metric(...)
```

> [!tip] O que `with` significa aqui?
> `with col_esq:` cria um **contexto**: tudo que está indentado abaixo dele pertence à coluna esquerda. Quando o bloco `with` termina (a indentação volta), voltamos a escrever no contexto anterior.
>
> Pense assim: `with col_esq:` é como dizer "daqui até o fim do recuo, fala com a coluna esquerda".

### Visualizando o layout que vamos construir

```
┌─────────────────────────────────────────────────────────┐
│  Calculador de Torque — Motor de Indução Trifásico       │
│  [subtítulo]                                             │
├──────────────┬──────────────────────────┬───────────────┤
│   SIDEBAR    │   col_grafico (2/3)      │ col_metricas  │
│              │                          │    (1/3)      │
│ Tensão (V)   │  Curva T × s             │ T_max         │
│ Freq (Hz)    │  ┌──────────────────┐    │ s_Tmax        │
│ Polos        │  │                  │    │ T_partida     │
│              │  │    gráfico       │    │ RPM_sinc      │
│ Rs           │  │                  │    │ ──────────    │
│ Xs           │  └──────────────────┘    │ slider s      │
│ Xm           │                          │ Te(s)         │
│ Rr           │                          │               │
│ Xr           │                          │               │
└──────────────┴──────────────────────────┴───────────────┘
```

Esse é o layout que vamos construir. Cada região tem uma responsabilidade clara:
- **Sidebar:** toda a entrada de parâmetros
- **col_grafico:** a curva de torque completa (precisa de espaço)
- **col_metricas:** valores numéricos derivados + slider interativo

### Outros elementos de layout úteis

Além de colunas e sidebar, o Streamlit oferece mais dois mecanismos que vamos usar:

**`st.divider()`** — insere uma linha horizontal. Separa grupos de elementos visualmente sem criar nova coluna.

```python
st.metric("Torque máximo", "45.8 N·m")
st.divider()
st.subheader("Ponto específico")
```

**`st.subheader()` e `st.header()`** — títulos menores que organizam o conteúdo de cada seção da página.

```python
st.title("Título principal")      # maior
st.header("Seção grande")         # médio
st.subheader("Subseção")          # menor
st.markdown("texto normal")       # parágrafo
```

### Testando o modelo mental

Antes de construir a interface completa, teste o esqueleto de layout isolado. Crie um arquivo temporário `teste_layout.py` na pasta `PILOTO`:

```python
import streamlit as st

st.set_page_config(layout="wide")
st.title("Teste de layout")

# Sidebar
st.sidebar.header("Parâmetros")
st.sidebar.number_input("Valor A", value=10.0)
st.sidebar.number_input("Valor B", value=20.0)

# Conteúdo principal em duas colunas
col_esq, col_dir = st.columns([2, 1])

with col_esq:
    st.subheader("Área do gráfico")
    st.write("(aqui vai o gráfico)")

with col_dir:
    st.subheader("Métricas")
    st.metric("Resultado A", "42")
    st.divider()
    st.metric("Resultado B", "99")
```

Execute:
```
streamlit run teste_layout.py
```

Você verá a estrutura exata sem nenhum cálculo real. **Confirme que o layout faz sentido visual antes de adicionar o código de simulação.** Esse é o processo de um desenvolvedor de interfaces: montar o esqueleto primeiro, preenchê-lo depois.

Quando estiver satisfeito com o layout, delete `teste_layout.py` — ele foi só um rascunho.

> [!note] Conceito fixado
> Layout Streamlit = três zonas (sidebar / col_esquerda / col_direita). `st.sidebar.` direciona para a barra lateral. `st.columns([2,1])` divide o conteúdo principal. `with coluna:` direciona elementos para aquela coluna específica.

---

## Parte 11 — Construindo a interface visual passo a passo

> [!info] Funções Streamlit introduzidas nesta parte
>
> | Função | O que faz | Como usar |
> |---|---|---|
> | `st.sidebar.selectbox("rótulo", options=[...], index=N)` | Lista suspensa na sidebar. `index` define item padrão (0 = primeiro). | `st.sidebar.selectbox("Polos", [2,4,6,8], index=1)` |
> | `st.line_chart(dataframe)` | Gráfico de linhas a partir de um DataFrame Pandas | `st.line_chart(df.set_index("Escorregamento"))` |
> | `pd.DataFrame({"col": lista})` | Cria uma tabela (DataFrame) com colunas nomeadas | `pd.DataFrame({"s": s_vals, "Te": te_vals})` |
> | `df.set_index("coluna")` | Define uma coluna como índice (eixo X do gráfico) | `df.set_index("Escorregamento")` |
> | `st.metric("rótulo", "valor")` | Exibe um valor destacado com rótulo — ideal para KPIs | `st.metric("Torque máximo", "45.8 N·m")` |
> | `st.slider("rótulo", min, max, value, step)` | Controle deslizante. Devolve o valor atual escolhido pelo usuário. | `s = st.slider("s", 0.001, 1.0, 0.05, 0.001)` |
> | `max(lista)` | Retorna o maior valor de uma lista | `t_max = max(torques)` |
> | `lista.index(valor)` | Retorna o índice (posição) de um valor na lista | `idx = torques.index(t_max)` |

### O plano

Vamos construir `app_piloto.py` em incrementos. Cada incremento adiciona um elemento e testa:

```
Título + configuração da página
       ↓
Painel lateral com parâmetros
       ↓
Cálculo dos resultados
       ↓
Coluna com gráfico + coluna com métricas
       ↓
Slider para explorar um ponto específico
```

---

### Incremento 10.1 — Configuração e título

Abra `app_piloto.py` e substitua tudo pelo seguinte:

```python
import streamlit as st
import numpy as np
import math
import motor_functions as mf

st.set_page_config(
    page_title="Calculador de Torque",
    layout="wide"
)

st.title("Calculador de Torque — Motor de Indução Trifásico")
st.markdown("Ajuste os parâmetros na barra lateral para visualizar a curva de torque.")
```

> [!tip] `st.set_page_config()`
> Deve ser o **primeiro** comando Streamlit do arquivo. `page_title` define o nome na aba do navegador. `layout="wide"` usa toda a largura da tela — essencial para exibir gráfico e métricas lado a lado.

> [!tip] `st.markdown()`
> Exibe texto com formatação Markdown. Pode usar `**negrito**`, `*itálico*`, listas, links, etc.

Execute e veja o título aparecendo na página.

---

### Incremento 10.2 — Painel lateral com os parâmetros

Adicione abaixo do título:

```python
st.sidebar.header("Parâmetros do Motor")

tensao_linha = st.sidebar.number_input(
    "Tensão de linha (V)",
    min_value=100.0,
    max_value=15000.0,
    value=380.0,
    step=10.0
)

frequencia = st.sidebar.number_input(
    "Frequência (Hz)",
    min_value=50.0,
    max_value=60.0,
    value=60.0,
    step=10.0
)

num_polos = st.sidebar.selectbox(
    "Número de polos",
    options=[2, 4, 6, 8],
    index=1
)
```

> [!tip] `st.sidebar.alguma_coisa()`
> Tudo que começa com `st.sidebar.` aparece na barra lateral esquerda, não no conteúdo principal. Ideal para parâmetros de configuração — mantém o painel principal limpo para gráficos e resultados.

> [!tip] Parâmetros de `st.sidebar.number_input()`
> - `min_value` / `max_value` — limites aceitos (Python rejeita valores fora desse intervalo)
> - `value` — valor padrão ao abrir a página
> - `step` — incremento ao clicar nas setas do campo

> [!tip] `st.sidebar.selectbox()`
> Lista suspensa. `options` é a lista de opções válidas. `index=1` seleciona o segundo item (índice 1 = `4`) como padrão. Em Python, listas começam no índice 0.

Adicione também os parâmetros do circuito equivalente:

```python
st.sidebar.subheader("Circuito Equivalente")

Rs = st.sidebar.number_input("Rs — Resistência do estator (Ω)", value=0.641, step=0.001, format="%.3f")
Xs = st.sidebar.number_input("Xs — Reatância dispersão estator (Ω)", value=1.106, step=0.001, format="%.3f")
Xm = st.sidebar.number_input("Xm — Reatância de magnetização (Ω)", value=26.3, step=0.1, format="%.2f")
Rr = st.sidebar.number_input("Rr — Resistência do rotor (Ω)", value=0.332, step=0.001, format="%.3f")
Xr = st.sidebar.number_input("Xr — Reatância dispersão rotor (Ω)", value=0.464, step=0.001, format="%.3f")
```

Execute. A barra lateral deve mostrar todos os campos. Mude um valor — nada acontece ainda no conteúdo principal porque ainda não calculamos nada.

---

### Incremento 10.3 — Cálculos

Adicione abaixo dos parâmetros:

```python
# Cálculos — executam toda vez que qualquer parâmetro muda
Vf            = mf.calcular_tensao_fase(tensao_linha)
omega_s       = mf.calcular_omega_sincrona(frequencia, num_polos)
Vth, Rth, Xth = mf.calcular_thevenin(Vf, Rs, Xs, Xm)

escorregamentos = np.linspace(0.001, 1.0, 200)
torques = []
for s in escorregamentos:
    Te = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s)
    torques.append(Te)
```

Isso não exibe nada — apenas calcula. Os resultados ficam nas variáveis `escorregamentos` e `torques`, prontos para serem exibidos no próximo incremento.

---

### Incremento 10.4 — Layout em duas colunas

Queremos o gráfico à esquerda e as métricas à direita. Para isso, usamos `st.columns()`.

```python
col_grafico, col_metricas = st.columns([2, 1])
```

Isso cria duas colunas. O `[2, 1]` define a proporção: a primeira ocupa 2/3 da largura, a segunda ocupa 1/3.

`col_grafico` e `col_metricas` são objetos que representam cada coluna. Para colocar algo numa coluna específica, usamos o bloco `with`:

```python
with col_grafico:
    st.write("Aqui vai o gráfico")

with col_metricas:
    st.write("Aqui vão as métricas")
```

---

### Incremento 10.5 — Gráfico

**Problema:** temos duas listas (`escorregamentos` e `torques`). `st.line_chart()` espera receber dados em formato de tabela, não duas listas separadas.

**Solução:** o Pandas é uma biblioteca para trabalhar com dados tabulares. Um `pd.DataFrame` é uma tabela com colunas nomeadas — exatamente o que `st.line_chart()` precisa.

```python
import pandas as pd

df = pd.DataFrame({
    "Escorregamento": escorregamentos,
    "Torque (N.m)": torques
})
```

Isso cria uma tabela com duas colunas: "Escorregamento" e "Torque (N.m)", onde cada linha é um ponto da curva.

`df.set_index("Escorregamento")` define a coluna "Escorregamento" como o eixo X do gráfico.

Substitua o `with col_grafico:` pelo código real:

```python
with col_grafico:
    st.subheader("Curva de Torque × Escorregamento")
    import pandas as pd
    df = pd.DataFrame({
        "Escorregamento": escorregamentos,
        "Torque (N.m)":   torques
    })
    st.line_chart(df.set_index("Escorregamento"))
```

Execute. O gráfico aparece no conteúdo principal. Mude um parâmetro na barra lateral — o gráfico atualiza.

---

### Incremento 10.6 — Métricas e slider

Agora a coluna direita. Queremos mostrar:
- Torque máximo e em qual escorregamento ocorre
- Torque de partida (s=1)
- Velocidade síncrona em RPM
- Torque para um escorregamento específico escolhido pelo usuário

```python
with col_metricas:
    st.subheader("Métricas")

    torque_maximo  = max(torques)
    idx_max        = torques.index(torque_maximo)
    s_torque_max   = escorregamentos[idx_max]
    torque_partida = torques[-1]
    rpm_sincrona   = omega_s * 60 / (2 * math.pi)

    st.metric("Torque máximo", f"{torque_maximo:.1f} N·m")
    st.metric("Escorregamento no T_max", f"{s_torque_max:.3f}")
    st.metric("Torque de partida (s=1)", f"{torque_partida:.1f} N·m")
    st.metric("Velocidade síncrona", f"{rpm_sincrona:.0f} RPM")

    st.divider()

    st.subheader("Ponto específico")
    s_esp = st.slider(
        "Escorregamento",
        min_value=0.001,
        max_value=1.0,
        value=0.05,
        step=0.001,
        format="%.3f"
    )
    Te_esp = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s_esp)
    st.metric(f"Te para s={s_esp:.3f}", f"{Te_esp:.2f} N·m")
```

> [!tip] `max(lista)` e `lista.index(valor)`
> `max(torques)` retorna o maior valor da lista. `torques.index(valor)` retorna a posição (índice) onde esse valor aparece. Usamos o índice para encontrar o escorregamento correspondente em `escorregamentos[idx_max]`.

> [!tip] `torques[-1]`
> Índice `-1` acessa o **último** elemento da lista. Como `escorregamentos` vai de 0.001 a 1.0, `torques[-1]` é o torque para s=1.0 (torque de partida).

> [!tip] `st.metric(rótulo, valor)`
> Exibe um valor destacado com rótulo. Ideal para KPIs e resultados principais.

> [!tip] `st.slider()`
> Cria um controle deslizante. O usuário arrasta para escolher um valor no intervalo. `format="%.3f"` exibe o valor com 3 casas decimais.

> [!tip] `st.divider()`
> Linha horizontal de separação visual.

Execute a versão final. A interface completa deve estar funcionando: gráfico à esquerda, métricas e slider à direita, barra lateral com todos os parâmetros.

---

## Parte 12 — Código completo consolidado

Após construir cada parte incrementalmente, aqui estão os arquivos finais para referência.

### `motor_functions.py`

```python
import math


def calcular_tensao_fase(tensao_linha):
    """Converte tensão de linha para tensão de fase (sistema trifásico)."""
    return tensao_linha / math.sqrt(3)


def calcular_omega_sincrona(frequencia, num_polos):
    """Calcula a velocidade angular síncrona em rad/s."""
    return (2 * math.pi * frequencia) / (num_polos / 2)


def calcular_thevenin(tensao_fase, Rs, Xs, Xm):
    """Retorna (Vth, Rth, Xth) — equivalente de Thevenin do circuito do motor."""
    Vth = tensao_fase * (Xm / math.sqrt(Rs**2 + (Xs + Xm)**2))
    Rth = Rs * (Xm / (Xs + Xm))**2
    Xth = (Xs * Xm) / (Xs + Xm)
    return Vth, Rth, Xth


def calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s):
    """Calcula o torque eletromagnético [N.m] para escorregamento s."""
    numerador   = 3 * Vth**2 * (Rr / s)
    denominador = omega_s * ((Rth + Rr/s)**2 + (Xth + Xr)**2)
    return numerador / denominador
```

---

### `calculador_torque.py`

```python
import numpy as np
import motor_functions as mf

# Parâmetros
tensao_linha = 380.0
frequencia   = 60.0
num_polos    = 4
Rs = 0.641
Xs = 1.106
Xm = 26.3
Rr = 0.332
Xr = 0.464

# Cálculos intermediários
Vf            = mf.calcular_tensao_fase(tensao_linha)
omega_s       = mf.calcular_omega_sincrona(frequencia, num_polos)
Vth, Rth, Xth = mf.calcular_thevenin(Vf, Rs, Xs, Xm)

# Torque para um ponto
s  = 0.05
Te = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s)
print(f"Torque para s={s}: {Te:.2f} N.m")

# Curva completa
print(f"\n{'s':>6}  {'Te (N.m)':>10}")
print("-" * 20)
for s in np.linspace(0.01, 1.0, 20):
    Te = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s)
    print(f"{s:>6.3f}  {Te:>10.2f}")
```

---

### `app_piloto.py`

```python
import streamlit as st
import numpy as np
import pandas as pd
import math
import motor_functions as mf

st.set_page_config(page_title="Calculador de Torque", layout="wide")
st.title("Calculador de Torque — Motor de Indução Trifásico")
st.markdown("Ajuste os parâmetros na barra lateral para visualizar a curva de torque.")

# Barra lateral — parâmetros
st.sidebar.header("Parâmetros do Motor")
tensao_linha = st.sidebar.number_input("Tensão de linha (V)", min_value=100.0, max_value=15000.0, value=380.0, step=10.0)
frequencia   = st.sidebar.number_input("Frequência (Hz)", min_value=50.0, max_value=60.0, value=60.0, step=10.0)
num_polos    = st.sidebar.selectbox("Número de polos", options=[2, 4, 6, 8], index=1)

st.sidebar.subheader("Circuito Equivalente")
Rs = st.sidebar.number_input("Rs — Resistência do estator (Ω)", value=0.641, step=0.001, format="%.3f")
Xs = st.sidebar.number_input("Xs — Reatância dispersão estator (Ω)", value=1.106, step=0.001, format="%.3f")
Xm = st.sidebar.number_input("Xm — Reatância de magnetização (Ω)", value=26.3, step=0.1, format="%.2f")
Rr = st.sidebar.number_input("Rr — Resistência do rotor (Ω)", value=0.332, step=0.001, format="%.3f")
Xr = st.sidebar.number_input("Xr — Reatância dispersão rotor (Ω)", value=0.464, step=0.001, format="%.3f")

# Cálculos
Vf            = mf.calcular_tensao_fase(tensao_linha)
omega_s       = mf.calcular_omega_sincrona(frequencia, num_polos)
Vth, Rth, Xth = mf.calcular_thevenin(Vf, Rs, Xs, Xm)

escorregamentos = np.linspace(0.001, 1.0, 200)
torques = []
for s in escorregamentos:
    torques.append(mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s))

# Layout principal
col_grafico, col_metricas = st.columns([2, 1])

with col_grafico:
    st.subheader("Curva de Torque × Escorregamento")
    df = pd.DataFrame({"Escorregamento": escorregamentos, "Torque (N.m)": torques})
    st.line_chart(df.set_index("Escorregamento"))

with col_metricas:
    st.subheader("Métricas")
    torque_maximo  = max(torques)
    idx_max        = torques.index(torque_maximo)
    s_torque_max   = escorregamentos[idx_max]
    torque_partida = torques[-1]
    rpm_sincrona   = omega_s * 60 / (2 * math.pi)

    st.metric("Torque máximo", f"{torque_maximo:.1f} N·m")
    st.metric("Escorregamento no T_max", f"{s_torque_max:.3f}")
    st.metric("Torque de partida (s=1)", f"{torque_partida:.1f} N·m")
    st.metric("Velocidade síncrona", f"{rpm_sincrona:.0f} RPM")

    st.divider()

    st.subheader("Ponto específico")
    s_esp  = st.slider("Escorregamento", min_value=0.001, max_value=1.0, value=0.05, step=0.001, format="%.3f")
    Te_esp = mf.calcular_torque(omega_s, Vth, Rth, Xth, Rr, Xr, s_esp)
    st.metric(f"Te para s={s_esp:.3f}", f"{Te_esp:.2f} N·m")
```

---

## Parte 13 — Como salvar e organizar a pasta PILOTO

### Estrutura de arquivos

A pasta `PILOTO` deve ter exatamente esta estrutura:

```
PILOTO/
├── Tutorial_Componente_Piloto.md   ← este arquivo
├── motor_functions.py              ← funções de cálculo (núcleo físico)
├── calculador_torque.py            ← script de terminal
└── app_piloto.py                   ← interface Streamlit
```

### Onde criar a pasta

Dentro do repositório IWS, na raiz:

```
c:\Users\gacas\OneDrive\Códigos\IWS\PILOTO\
```

### Como executar cada arquivo

No terminal, navegue até a pasta:

```
cd c:\Users\gacas\OneDrive\Códigos\IWS\PILOTO
```

Script de terminal (teste sem interface):
```
python calculador_torque.py
```

Interface web:
```
streamlit run app_piloto.py
```

O Streamlit abrirá automaticamente no navegador. Se não abrir, acesse `http://localhost:8501`.

### O que cada arquivo representa no IWS real

| Arquivo do piloto | Equivalente no IWS |
|---|---|
| `motor_functions.py` | `core/machine_model.py` — modelo dq0 completo |
| `calculador_torque.py` | `core/IWS_PY.py` — fachada pública com `run_simulation()` |
| `app_piloto.py` | `IWS_UI.py` + `ui/clean_view.py` — orquestrador e layout |
| `st.sidebar.number_input()` | `ui_components/sim_config.py` — painel de parâmetros |
| `st.line_chart()` | `viz/plotly_charts.py` — gráficos Plotly interativos |

A arquitetura do piloto, em escala reduzida, é a mesma do IWS:
- Núcleo físico separado da interface
- Funções puras (sem efeitos colaterais) no módulo de cálculo
- Interface declarativa que lê parâmetros e exibe resultados

---

> [!success] Síntese do que você construiu
> Você partiu de zero e construiu:
> - Um módulo de funções físicas (`motor_functions.py`)
> - Um script de terminal que calcula a curva de torque
> - Uma aplicação web interativa com parâmetros, gráfico e métricas
>
> Cada passo partiu de um problema concreto. Cada ferramenta Python foi introduzida no momento em que resolvia esse problema específico. Os três arquivos na pasta `PILOTO` são o ponto de partida para entender e expandir o simulador IWS.

---

*Tutorial gerado em 2026-05-25 para o projeto IWS — Infraestrutura Web de Simulação.*
