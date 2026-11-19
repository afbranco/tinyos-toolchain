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
  2. **Terra** (`afbranco/Terra`): compila a VM dentro desta imagem e publica releases do
     `_TOSSIMmodule.so`. Expectativa do Prof.: o Terra não precisará de adaptação.
  3. **TerraSim** (`~/TerraSim`): troca o `.so` vendorizado por uma release do Terra, depois de
     passar por um oráculo de equivalência.

## Decisões já tomadas (2026-11-19)

- Repositório **público** `afbranco/tinyos-toolchain` (aprovado pelo Prof.; ainda **não criado**
  no GitHub quando este arquivo foi escrito: criar a partir desta pasta).
- Releases = **tags da imagem**: `2.1.2-jammy-py2` (feito), depois `2.1.2-<ubuntu>-py3`.
- O TinyOS vem do oficial (`tinyos/tinyos-main`, tag `release_tinyos_2_1_2`), conferido por
  SHA-256. O fork `afbranco/tinyos-main` é uma cópia pura do `master` de 2017 (0 commits
  próprios, 36 atrás): **não serve de base como está**. Ele entra quando a primeira alteração no
  TinyOS for necessária (provavelmente o SWIG 4 do Python 3), numa **branch criada a partir da
  tag 2.1.2**, não do `master`.

## Pendências para decidir com o Prof.

- **Licença** do repositório (o TinyOS é BSD). Sem licença, um repositório público fica "todos
  os direitos reservados".
- **Inventário da `.ova`** (Ubuntu 12.04 com o ambiente antigo do Prof.): ele tem alterações não
  testadas, e elas podem estar dentro de `/opt/tinyos-2.1.2` na VM, além do Terra. Comparar a
  árvore de lá com a tag oficial; diferenças viram os primeiros commits da branch do fork. O
  7-Zip já está instalado (`7z`) e extrai o disco sem ligar a VM. Pedir o caminho da `.ova`.

## O que já se sabe do build em produção

O `_TOSSIMmodule.so` que o TerraSim usa (`~/TerraSim/legacy/TerraNG/sim/Net/`) traz informação
de depuração: GCC 4.6.3 (Ubuntu 12.04), TinyOS em `/opt/tinyos-2.1.2`, SWIG 1.3.31, alvo
`micaz sim-sf`, Python 2.7 de 32 bits, compilado em `/home/branco/gitspace/Terra/TerraVM/src`
(com pastas `CustomVMs/TerraNet` e `XComps` que **não existem** no GitHub do Terra). Ou seja, o
código em produção é anterior ao publicado.

## Próximo passo técnico

Python 3: regerar os bindings com SWIG 4 a partir de `tos/lib/tossim/tossim.i`,
`tos/lib/tossim/sf/SerialForwarder.i` e `sf/Throttle.i`, e adaptar `sim.extra`/`sim-sf.extra`
(Python 3 muda `Py_InitModule`, strings e o nome da biblioteca). Começar no 22.04 (`jammy-py3`),
depois tentar o 24.04.

## Como trabalhar

- **Testar antes de publicar**: `tests/smoke.sh` dentro da imagem tem de dar `ALL PASS`.
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
