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
     `_TOSSIMmodule.so`. Expectativa do Prof.: o Terra não precisará de adaptação. Atenção: no
     Python 3 o módulo se chama `_TOSSIM.so`, então quem publica ou copia o `.so` muda o nome.
  3. **TerraSim** (`~/TerraSim`): troca o `.so` vendorizado por uma release do Terra, depois de
     passar por um oráculo de equivalência.

## Decisões já tomadas (2026-11-19)

- Repositório **público** `afbranco/tinyos-toolchain`, licença **BSD 3-Clause** (aprovados pelo
  Prof.; criado em 2026-11-21).
- Releases = **tags da imagem**: `2.1.2-jammy-py2` e `2.1.2-jammy-py3` (feitos), depois
  `2.1.2-noble-py3`.
- O TinyOS vem do oficial (`tinyos/tinyos-main`, tag `release_tinyos_2_1_2`), conferido por
  SHA-256. Alterações no TinyOS ficam no fork `afbranco/tinyos-main`, branch **`tossim-py3`**,
  criada a partir da tag 2.1.2 (o `master` do fork é cópia de 2017 e não serve de base). Clone
  local raso em `~/tinyos-main`. O `jammy-py3` fixa o commit da branch e o SHA-256 do tarball:
  commit novo na branch exige atualizar os dois no Containerfile.
- Python 3 (2026-11-21, aprovado pelo Prof.): um único commit com os wrappers regerados pelo
  SWIG 4.0.2 e **commitados** (a imagem não precisa de SWIG); o mesmo fonte serve Python 2.7 e 3.
  O módulo passou a `_TOSSIM.so`; `setData`/`data()` usam `bytes` no Python 3. A SDK Python do
  TinyOS (`support/sdk/python`) continua só Python 2 e não foi portada.

## Pendências para decidir com o Prof.

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

Ubuntu 24.04 (`noble-py3`, Python 3.12): conferir se o GCC 10 ainda existe no apt (fix 6) e se os
wrappers do SWIG 4.0.2 compilam com o Python 3.12. Depois, o oráculo de equivalência (fixar a
semente com `randomSeed`: por padrão ela vem do relógio).

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
