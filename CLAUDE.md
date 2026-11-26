# tinyos-toolchain: guia para o Claude Code

Este projeto nasceu numa sessão do TerraSim (2026-11-19). Este arquivo leva o contexto para a
sessão própria dele. O README (em inglês, porque o repositório é público) descreve o projeto; aqui
ficam as decisões e o modo de trabalhar.

## Quem e o quê

- O dono é o Prof. Adriano Branco (PUC-Rio). Conversar com ele em **português do Brasil**.
  Ele não gosta de travessão ("—"): usar dois-pontos, ponto ou parênteses.
- Objetivo: gerar o **TinyOS 2.1.2 + TOSSIM num ambiente atual**, como imagem de container, sem
  mexer no TinyOS enquanto der. **Meta declarada pelo Prof.: chegar ao Python 3.**
- Três projetos em cadeia, cada um consumindo o anterior como artefato pronto:
  1. **tinyos-toolchain** (este): só o toolchain, sem nada de Terra.
  2. **Terra** (`afbranco/Terra`, clone em `~/Terra` com `CLAUDE.md` próprio, criado em
     2026-11-21 para a sessão Terra): compila a VM dentro desta imagem e publica releases do
     `_TOSSIMmodule.so`. Expectativa do Prof.: o Terra não precisará de adaptação. Atenção: no
     Python 3 o módulo se chama `_TOSSIM.so`, então quem publica ou copia o `.so` muda o nome.
  3. **TerraSim** (`~/TerraSim`): troca o `.so` vendorizado por uma release do Terra, depois de
     passar por um oráculo de equivalência.

## Decisões já tomadas (2026-11-19)

- Repositório **público** `afbranco/tinyos-toolchain`, licença **BSD 3-Clause** (aprovados pelo
  Prof.; criado em 2026-11-21).
- Releases = **tags da imagem**. Mantida: `2.1.2-resolute-py3` (Ubuntu 26.04). Congelada:
  `2.1.2-jammy-py2` (não recebe trabalho novo). O `jammy-py3` foi retirado (2026-11-21).
- **Escopo** (2026-11-21, decidido pelo Prof.): o compromisso é o TOSSIM, para o Terra. AVR
  (micaz, iris, mica2) entra com prazo limitado e só se cada correção for pequena. O resto
  (MSP430, ARM...) está fora: exigiria portar o TinyOS. Novas plataformas (ex.: nRF52) e portar
  o Terra são assuntos para depois, o segundo na sessão Terra.
- O TinyOS vem do oficial (`tinyos/tinyos-main`, tag `release_tinyos_2_1_2`), conferido por
  SHA-256. Alterações no TinyOS ficam no fork `afbranco/tinyos-main`, branch **`2.1.2-maintained`**
  (renomeada de `tossim-py3` em 2026-11-21, aprovado pelo Prof.),
  criada a partir da tag 2.1.2 (o `master` do fork é cópia de 2017 e não serve de base). Clone
  local raso em `~/tinyos-main`. O `resolute-py3` fixa o commit da branch e o SHA-256 do tarball:
  commit novo na branch exige atualizar os dois no Containerfile.
- Python 3 (2026-11-21, aprovado pelo Prof.): um único commit com os wrappers regerados pelo
  SWIG 4.0.2 e **commitados** (a imagem não precisa de SWIG); o mesmo fonte serve Python 2.7 e 3.
  O módulo passou a `_TOSSIM.so`; `setData`/`data()` usam `bytes` no Python 3. A SDK Python do
  TinyOS (`support/sdk/python`) continua só Python 2, exceto `tinyos.message.Message` (base das
  classes do `mig`), corrigido no fork (`0dca1d8`, aprovado pelo Prof. em 2026-11-21).
- `mig` (2026-11-21, pedido do Prof. para deixar a parte dele "íntegra"): correções 15 e 16 na
  imagem + `0dca1d8` no fork; testado por `tests/mig_check.py` (Python, Java e entrega no TOSSIM).
- `mig` no Terra (2026-11-21): com o `bc` (correção 17), o TerraVM público compila para micaz
  na imagem e as 6 classes Java do `mig` saem idênticas às commitadas no Terra (2018). O
  `libtoscomm` (serial do Java) vem pronto dentro do `tinyos.jar` e carrega; falta testar porta
  serial real no lab (SerialForwarder Java com a MIB520). Não usam `mig`: TerraSim (nada) e a
  saída Python/C. Sem teste: `mig` com arrays/strings em Python.
- Imagem publicada pelo GitHub Actions (`.github/workflows/images.yml`) em
  `ghcr.io/afbranco/tinyos-toolchain`, só com `ALL PASS`; pública (pull anônimo funciona).
- Releases marcadas (2026-11-22, aprovado pelo Prof., pedido da sessão Terra): tag git + GitHub
  Release `2.1.2-rN` apontando para uma imagem fixa (`2.1.2-resolute-py3-<commit>` + digest), com
  o que foi testado nela. **`2.1.2-r1`** = `f42bac7`, digest `sha256:7e21b1b9...`; as notas dizem
  "teste de laboratório pendente" (atualizar depois do teste do Prof. com a MIB520). Correção
  sai como `r2`; uma release publicada não muda. O Terra fixa a imagem da release, nunca a móvel.
- Scripts Python 2 do TinyOS (2026-11-22, achado pela sessão Terra, aprovado pelo Prof.: "os
  cinco"): `tos-storage-at45db/-stm25p/-pxa27xp30`, `tos-deluge`, `tos-dump.py`, mais o
  `tos-build-deluge-image` e o `tos.py` da SDK (necessários para os outros funcionarem), portados
  no fork (`9b530d6`, mais `5feb228`: `posix.environ` do `tos-deluge`, achado pelo smoke), compatíveis com Python 2 e 3. Correção 18: `python3-serial`. Decisão
  técnica: o `tos-storage-at45db` aloca os volumes na **ordem de dicionário do Python 2**
  (`py2_dict_order()`), senão o layout da flash muda (Deluge). Equivalência conferida contra os
  originais no Python 2.7 da `jammy-py2` (local), com um mote falso (`tests/fakemote.py`). O
  Terra só usa volumes no módulo opcional `MOD=VCN_DAT`. Publicado como **`2.1.2-r2`**
  (`21d8fb1`, digest `sha256:4198b123...`).
- Teste de laboratório (2026-11-26, imagem `r2`, 2 micaz em 2 MIB520CA; o Prof. viu os LEDs):
  gravação com `avrdude -cmib510`, rádio, serial nos dois sentidos com Python (`tos.py`,
  `tos-dump.py`, classe do `mig`) e Java (`Listen`, `TestSerial`, `PrintfClient`): passou
  (README, "Lab test"). Achou as correções 19 (`mig -target=null` sem as definições `_Float*`)
  e 20 (`javac -target 1.4`) e o `a2d2c126` do oficial (TestPrintf sem `SerialStartC`), no fork
  como `29a43b6`: os três aprovados pelo Prof. e publicados como **`2.1.2-r3`** (`0dded15`,
  imagem `2.1.2-resolute-py3-0dded15`, digest `sha256:e3da1ef0...`); notas r1 e r2 atualizadas
  com o resultado (a imagem delas não muda). Correção 19 no wrapper `gcc` (consulta `-dM`),
  20 num wrapper `javac`. A `jammy-py2` (congelada) tem os mesmos dois defeitos e fica sem eles.
  Na r3 vieram também atualizações de segurança do Ubuntu (binutils do host, krb5...); nesC,
  `tos/` e `support/` iguais à r2. Deluge fora do teste (decisão do Prof.).

## Pendências para decidir com o Prof.

- **Inventário da `.ova`** (feito em 2026-11-21): `TerraNG_v0.3.0.ova` do site do Terra
  (`www.inf.puc-rio.br/~prjterra/files/Terra/`, 2,34 GB, sem manifesto; SHA-256 do vmdk
  `3b78039c...`). Ubuntu 12.04.5 **i386**. TinyOS = pacote `tinyos-2.1.2` 2.1.2-20120813, **sem
  alterações** (difere da tag só por omissões do pacote e 2 arquivos mais antigos: rf212,
  shimmer). Ferramentas: **nesC 1.3.4**, gcc 4.6.3, avr-gcc 4.1.2 e avrdude 5.10 (pacotes do
  TinyOS), Python 2.7.3, Oracle Java 7, bc. Os `.so` do TerraSim são **idênticos** aos da
  `.ova` (2016-05-07); os do TerraDist no GitHub não. Fonte do Terra na `.ova`: só
  `/home/terra/Downloads/Terra-master(.zip)`, download do GitHub de **2015-04-21**, com o layout
  de produção (`CustomVMs`, `XComps`, `VMCustomNet.h`). Pela tabela de linhas (DWARF) do `.so`,
  o fonte de produção (2016) **não é** nem o de 2015 nem o do GitHub (2018): fica entre os dois
  (ex.: `TerraVMC.nc` bate com 2018 e não com 2015; `BasicServicesP.nc` e `VMCustomP.nc` (Net)
  não batem com nenhum). Cópia em scratchpad `ova/x/Terra-master` (scratchpad é temporário).
  **Versão base do `.so` de produção** (2026-11-21, pela tabela de linhas do DWARF, histórico
  completo do `afbranco/Terra`: 430 commits, 2014-06 a 2018-03; um clone raso tinha enganado):
  o fonte bate com o commit **`f02b8e6`** (2016-05-26, "Adaptação inicial para o Arduino Uno"):
  0 linhas além do fim e só 6-7 linhas sem código (o mesmo artefato do compilador visto no
  TinyOS), contra 80-90 no commit anterior (`b53382a`). O `BSUpload.nc` exclui o `74b669c` em
  diante. O `.so` é de 05-07: compilado com alterações locais commitadas em 05-26. Limite: edição
  na mesma linha não aparece; prova definitiva = recompilar `f02b8e6` com o toolchain da `.ova`.
  Depois do `f02b8e6`: 321 commits (37 na VM TinyOS) = as "inovações" a avaliar com o Prof.
  Layout de 2016 (`CustomVMs`, `XComps`) virou `platforms/TinyOS/*` em 2016-10-07.

## O que já se sabe do build em produção

O `_TOSSIMmodule.so` que o TerraSim usa (`~/TerraSim/legacy/TerraNG/sim/Net/`) traz informação
de depuração: GCC 4.6.3 (Ubuntu 12.04), TinyOS em `/opt/tinyos-2.1.2`, SWIG 1.3.31, alvo
`micaz sim-sf`, Python 2.7 de 32 bits, compilado em `/home/branco/gitspace/Terra/TerraVM/src`
(com pastas `CustomVMs/TerraNet` e `XComps` que **não existem** no GitHub do Terra). Ou seja, o
código em produção é anterior ao publicado.

## Próximo passo técnico

AVR (2026-11-21): Blink e RadioCountToLeds compilam para micaz, iris e mica2 na `resolute-py3`
(correções 12 e 13 no invólucro `resolute-py3/avr-gcc` + `cbbddf66` do oficial no fork), e o
micaz roda no **Avrora** 1.7.117 dentro do `smoke.sh` (JDK 17: o Avrora não roda no 21). O jar
fica em `third_party/avrora` (decisão do Prof., 2026-11-21: os espelhos do SourceForge falham).
Também mica2dot (compila sem correção nova). Gravação: `avrdude` com `PROGRAMMER=avrdude`
(correção 14: o `uisp` do Ubuntu não é o modificado pelo TinyOS). O Prof. tem no lab micaz,
mica2, mica2dot e telosb (este fora do escopo), placa MIB520 (USB) e talvez uma MIB600
(ethernet). Falta: mote real (o Prof. testa na semana de 2026-11-23).

64 bits: a varredura de avisos do GCC nos builds TOSSIM não acha conversão ponteiro/inteiro.
O Prof. lembrava de um problema de 64 bits identificado na VM do Terra, numa sessão TerraSim
anterior. A sessão TerraSim (2026-11-21) não tem registro: buscou docs, memórias, git log e a
transcrição; só consta que o `.so` é i386 e roda sob x86_64. Os `.so` publicados do Terra são
todos i386. Origem do diagnóstico em aberto (perguntar ao Prof. onde ele viu). Depois: oráculo de equivalência (fixar a semente com `randomSeed`).

## Como trabalhar

- **Testar antes de publicar**: `tests/smoke.sh` dentro da imagem tem de dar `ALL PASS`. Ele
  inclui o teste do C gerado (`tests/ref/`): é o mapa de impacto de qualquer mudança no fork ou
  na toolchain. Mudança intencional: regerar as referências e commitar junto, explicando.
- **Painel de status**: ao concluir uma tarefa que muda o estado do projeto (release, teste,
  decisão), e antes de encerrar, atualizar o painel em `STATUS.md` (fora do git, em
  `.git/info/exclude`, porque o repositório é público). Criado pela sessão `~/admin` em
  2026-11-23: na primeira abertura, conferir o conteúdo.
- `PFLAGS` vai pelo **ambiente**, nunca na linha de comando do `make`: na linha de comando ele
  anula o `PFLAGS +=` do `sim.extra` e o build deixa de ser de simulação.
- **Teste novo só vale depois de reprovar com a mudança desfeita** (mutar o teste).
- A máquina é a do Prof.: builds pesados com `nice -n 19`, e avisar antes de carga grande.
- Matar processo só por PID. Restaurar a partir de cópias, nunca `git checkout`/`restore`/`stash`
  por cima de trabalho.
- Não mostrar credenciais nem cookies.
- Commit/push e PR: perguntar antes de abrir PR. Como o repositório é público, o GitHub Actions é
  gratuito (não consome o orçamento de CI do TerraSim).
- Commits terminam com:
  ```
  Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
  ```
