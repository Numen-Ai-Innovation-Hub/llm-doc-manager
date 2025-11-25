# Proposta Final Consolidada - Sistema de Documentação Automática

## 🎯 PROPOSTA FINAL CONSOLIDADA

### A. Estrutura de `docs/` (Simplificada e Focada)

```
docs/
├── readme.md              # Overview do projeto
├── index.md               # Navegação/índice
├── architecture.md        # Visão arquitetural
├── glossary.md            # Termos do domínio
├── whereiwas.md           # Jornal de desenvolvimento
├── index.json             # Índice estruturado para RAG
│
└── api/                   # Documentação completa (espelha src/)
    ├── src/
    │   ├── scanner.md     # Doc completa: técnica + conceitual
    │   ├── processor.md
    │   ├── queue.md
    │   └── ...
    └── utils/
        ├── marker_detector.md
        └── ...
```

**Características:**
- ✅ **Uma pasta só** (`api/`) em vez de `reference/` + `modules/`
- ✅ **Espelha estrutura** de `src/`
- ✅ **Doc completa por arquivo**: técnica (API) + conceitual (propósito, deps, I/O)
- ✅ **Só documenta arquivos com markers processados**

---

### B. Quando a Documentação é Gerada

**Workflow:**
```
1. sync → detecta markers (@llm-doc, @llm-class, @llm-comm, @llm-module)
2. process → gera docstrings via LLM
3. review → usuário aceita
4. apply → aplica no código
5. sync (novamente) → ✅ Queue vazia (sem pendências)
   └─> AGORA gera docs/
```

**Lógica de bloqueio:**
```python
# Em cli.py - comando sync (estendido)

if queue_manager.count_pending_tasks() > 0:
    click.echo("⚠️  Há tarefas pendentes. Execute process → review → apply primeiro.")
    return  # NÃO gera docs/

# Queue limpa - todos os markers processados
click.echo("\n✅ Todos os markers processados. Gerando documentação...")
generator = DocsGenerator(config)
generator.generate_all_docs()
```

**Garantia de padronização:**
- ✅ Só gera docs quando **todos** os arquivos têm docstrings completas
- ✅ Módulos sem `@llm-module` → não gera doc (ou gera aviso)
- ✅ Consistência: Google Style em todos os docstrings

---

### C. Conteúdo de Cada Arquivo em `docs/api/`

**Exemplo: `docs/api/src/scanner.md`**

```markdown
---
# YAML Front Matter para RAG
type: module_documentation
module_path: src/scanner.py
module_name: scanner
exports: [Scanner, ScanResult]
dependencies:
  internal: [src.config, utils.marker_detector, utils.marker_validator]
  external: [pathlib, typing]
complexity: medium
lines_of_code: 213
last_updated: 2025-11-24T10:30:00
source_hash: abc123def456
tags: [scanning, detection, validation, markers]
---

# Scanner Module

## Overview

[Extrai do module docstring gerado por @llm-module]

Scans project files to detect documentation markers. Coordinates between
MarkerDetector (low-level pattern matching) and MarkerValidator (validation logic).

## Purpose

**What it does:**
- Discovers Python files in project
- Detects `@llm-doc`, `@llm-class`, `@llm-comm` markers
- Validates marker syntax and balance
- Returns scan results with validation issues

**When to use:**
Called by CLI `sync` command to discover documentation needs.

## Dependencies

### Internal
- `Config` (src.config) - Configuration management
- `MarkerDetector` (utils.marker_detector) - Pattern matching
- `MarkerValidator` (utils.marker_validator) - Validation logic

### External
- `pathlib` - File operations
- `typing` - Type hints

## Input/Output

**Input:**
- `paths` (List[str], optional) - Directories to scan
- Uses `config.paths_to_scan` if not provided

**Output:**
- `ScanResult` object containing:
  - `files_scanned` (int)
  - `blocks_found` (int)
  - `validation_issues` (List[ValidationIssue])

## Exceptions

| Exception | When | Resolution |
|-----------|------|------------|
| `FileNotFoundError` | Path doesn't exist | Check config.paths_to_scan |
| `PermissionError` | Cannot read files | Check file permissions |

## Side Effects

- Reads filesystem (multiple files)
- Caches validation results in `file_validations` table
- Updates database on successful validation

## API Reference

### Classes

#### `Scanner`

[Extrai do class docstring]

**Initialization:**
```python
Scanner(config: Config)
```

**Methods:**

##### `scan(paths: Optional[List[str]] = None) -> ScanResult`

[Extrai do method docstring]

Scans files for documentation markers.

**Parameters:**
- `paths` (List[str], optional): Paths to scan

**Returns:**
- `ScanResult`: Scan results with validation

**Example:**
```python
from llm_doc_manager.src.scanner import Scanner

config = Config()
scanner = Scanner(config)
result = scanner.scan(['src/'])
```

### Data Classes

#### `ScanResult`

[Extrai do class docstring se existir]

Container for scan results.

**Attributes:**
- `files_scanned` (int)
- `blocks_found` (int)
- `validation_issues` (List[ValidationIssue])

## Usage Examples

[Gerado via LLM analisando o código]

```python
# Example 1: Basic scan
scanner = Scanner(config)
result = scanner.scan()
print(f"Found {result.blocks_found} blocks")

# Example 2: Scan specific path
result = scanner.scan(['src/utils/'])
if result.has_errors():
    print("Validation errors found!")
```

## Related Modules

- [ChangeDetector](detector.md) - Uses scan results for change detection
- [MarkerDetector](../utils/marker_detector.md) - Low-level detection logic
- [Config](config.md) - Configuration management

## Implementation Notes

- Uses `pathlib.Path.rglob('**/*.py')` for file discovery
- Respects `.gitignore` if present
- Performance: O(n × m) where n=files, m=lines per file
- Caching: Validation cached in database

---

**Source:** [`src/scanner.py`](../../src/scanner.py)
**Last Updated:** 2025-11-24T10:30:00
**Auto-generated:** Yes
```

---

### D. RAG para IA - O que é Necessário

Para que uma IA entenda o projeto sem ler todo o código:

#### 1. Índice Estruturado (`docs/index.json`)

```json
{
  "project": {
    "name": "llm-doc-manager",
    "version": "0.3.0",
    "description": "Automated Python docstring generation with hash-based change detection",
    "language": "python",
    "python_version": "3.8+",
    "entry_points": {
      "cli": "llm_doc_manager.src.cli:cli",
      "main": "llm_doc_manager.__main__"
    },
    "architecture_pattern": "layered",
    "layers": ["cli", "processing", "foundation"]
  },

  "modules": [
    {
      "path": "src/scanner.py",
      "name": "scanner",
      "type": "service",
      "purpose": "File scanning and marker detection",
      "layer": "processing",
      "exports": ["Scanner", "ScanResult"],
      "dependencies": {
        "internal": ["src.config", "utils.marker_detector"],
        "external": ["pathlib", "typing"]
      },
      "used_by": ["src.cli"],
      "doc_path": "docs/api/src/scanner.md",
      "lines_of_code": 213,
      "complexity": "medium",
      "last_updated": "2025-11-24T10:30:00",
      "source_hash": "abc123",
      "has_tests": true,
      "test_coverage": 85
    }
    // ... mais módulos
  ],

  "classes": [
    {
      "name": "Scanner",
      "module": "src.scanner",
      "type": "service_class",
      "purpose": "Coordinates file scanning operations",
      "public_methods": ["scan"],
      "dependencies": ["Config", "MarkerDetector", "MarkerValidator"],
      "doc_path": "docs/api/src/scanner.md#Scanner"
    }
    // ... mais classes
  ],

  "relationships": [
    {
      "from": "src.cli",
      "to": "src.scanner",
      "type": "uses",
      "context": "CLI sync command uses Scanner to detect markers"
    },
    {
      "from": "src.scanner",
      "to": "utils.marker_detector",
      "type": "depends_on",
      "context": "Scanner uses MarkerDetector for low-level pattern matching"
    }
    // ... mais relacionamentos
  ],

  "glossary": {
    "marker": "Delimiter comment (@llm-doc-start/end) indicating code block for documentation",
    "hash": "SHA256 checksum used for change detection",
    "task": "Database record representing documentation work to be done"
    // ... mais termos
  },

  "metadata": {
    "generated_at": "2025-11-24T10:30:00",
    "generator_version": "0.3.0",
    "total_modules": 15,
    "total_classes": 23,
    "total_functions": 87,
    "documentation_coverage": 95.5
  }
}
```

**Por que esse formato?**
- ✅ **Navegação rápida**: IA encontra módulos por `purpose` ou `name`
- ✅ **Grafo de dependências**: Entende como componentes se relacionam
- ✅ **Entry points**: Sabe onde começar a análise
- ✅ **Arquitetura clara**: Identifica padrão e camadas
- ✅ **Cobertura**: Vê o que está documentado

---

#### 2. Front Matter YAML em Cada `.md`

```yaml
---
type: module_documentation
module_path: src/scanner.py
module_name: scanner
exports: [Scanner, ScanResult]
dependencies:
  internal: [src.config, utils.marker_detector]
  external: [pathlib, typing]
complexity: medium
lines_of_code: 213
last_updated: 2025-11-24T10:30:00
source_hash: abc123def456
tags: [scanning, detection, validation]
---
```

**Por que front matter?**
- ✅ **Filtros rápidos**: IA pode fazer `type == "module_documentation"`
- ✅ **Semantic search**: Tags permitem busca por conceito
- ✅ **Change tracking**: `source_hash` indica se está desatualizado
- ✅ **Dependency graph**: IA monta grafo sem ler código

---

#### 3. Seções Estruturadas com Marcadores

Cada `.md` tem estrutura fixa:

```markdown
# [Nome do Módulo]

## Overview
[Resumo de 2-3 parágrafos]

## Purpose
[O que faz e quando usar]

## Dependencies
[Lista com links]

## Input/Output
[Contratos claros]

## Exceptions
[Tabela de erros]

## Side Effects
[O que altera fora do escopo]

## API Reference
[Classes e métodos]

## Usage Examples
[Código executável]

## Related Modules
[Links para docs relacionados]
```

**Por que estrutura fixa?**
- ✅ **Parsing fácil**: IA sabe onde procurar cada informação
- ✅ **Chunks naturais**: Cada seção = 1 chunk para embedding
- ✅ **Consistência**: Mesma estrutura em todos os arquivos

---

#### 4. Executive Summary (`docs/readme.md`)

```markdown
# Project Overview

**Name:** LLM Doc Manager
**Purpose:** Automated Python docstring generation
**Pattern:** Layered architecture (CLI → Processing → Foundation)

## Quick Understanding

This tool automates Python documentation using:
1. **Markers** - Explicit delimiters in code (`@llm-doc-start/end`)
2. **Hash-based detection** - Only process changed code (95% token savings)
3. **LLM generation** - Claude/GPT/Ollama generate docstrings
4. **Interactive review** - User validates before applying

## Entry Points

- **CLI:** `src/cli.py` - Main user interface
- **Core workflow:** sync → process → review → apply

## Key Components

1. **Scanner** (src/scanner.py) - Detects markers
2. **Processor** (src/processor.py) - LLM integration
3. **Queue** (src/queue.py) - Task management
4. **Applier** (src/applier.py) - Applies changes

## Architecture

```
[CLI Layer]
    ├─> Scanner → Detector → Queue
    └─> Processor → Applier

[Foundation]
    ├─> Database (SQLite)
    ├─> Markers (regex patterns)
    └─> Hashing (SHA256)
```

## Technology Stack

- Python 3.8+
- SQLite (queue/cache)
- Click (CLI)
- Anthropic/OpenAI/Ollama (LLM)

## Quick Start

```bash
llm-doc-manager init
llm-doc-manager sync
llm-doc-manager process
llm-doc-manager review
llm-doc-manager apply
```

[Link to full documentation: index.md]
```

**Por que executive summary?**
- ✅ **Contexto rápido**: IA entende projeto em 30 segundos
- ✅ **Entry points claros**: Sabe onde começar a explorar
- ✅ **Arquitetura visual**: Diagrama mostra relações
- ✅ **Stack tech**: Identifica dependências externas

---

### E. Arquivos a Criar (Lista Completa)

#### 1. Arquivos Raiz de `docs/`:

```
docs/
├── readme.md              ← Gerado via LLM (executive summary)
├── index.md               ← Gerado automaticamente (lista todos os docs)
├── architecture.md        ← Gerado via LLM (analisa imports + estrutura)
├── glossary.md            ← Gerado via LLM (extrai termos do código)
├── whereiwas.md           ← Gerado via git log + LLM
└── index.json             ← Gerado via AST parsing + metadata
```

#### 2. Arquivos em `docs/api/` (espelham `src/`):

Para **cada arquivo Python com markers processados**:

```
docs/api/
├── src/
│   ├── cli.md             ← Se src/cli.py tem @llm-module processado
│   ├── scanner.md         ← Se src/scanner.py tem @llm-module processado
│   ├── processor.md       ← ...
│   ├── queue.md
│   ├── applier.md
│   ├── detector.md
│   ├── hashing.md
│   ├── config.md
│   ├── database.md
│   └── constants.md
│
└── utils/
    ├── marker_detector.md
    ├── marker_validator.md
    ├── docstring_handler.md
    ├── content_hash.md
    └── logger_setup.md
```

**Estrutura de cada arquivo:** (como mostrado no exemplo `scanner.md` acima)
- Front matter YAML (metadados RAG)
- Overview (module docstring)
- Purpose
- Dependencies
- Input/Output
- Exceptions
- Side Effects
- API Reference (classes/functions com docstrings)
- Usage Examples
- Related Modules

---

### F. Como São Gerados (Fontes de Informação)

| Arquivo | Fonte de Dados | Método de Geração |
|---------|----------------|-------------------|
| **readme.md** | README raiz + architecture.md | LLM sumariza em executive summary |
| **index.md** | Lista de arquivos em docs/ | Script Python (lista dinâmica) |
| **architecture.md** | AST parsing (imports) + estrutura pastas | LLM analisa dependências e identifica padrão |
| **glossary.md** | Nomes de classes/funções/variáveis + docstrings | LLM extrai termos técnicos e define |
| **whereiwas.md** | `git log --since="30 days"` | LLM agrupa commits por tema |
| **index.json** | AST parsing + module docstrings + imports | Script Python (análise estática) |
| **api/*.md** | Module/class/function docstrings + AST | LLM formata seguindo template |

---

### G. Atualização Automática (Change Detection)

```python
# Trigger de regeneração em cli.py (comando sync)

# 1. Detecta mudanças no código (já existe)
changed_files = detector.detect_changes()

# 2. Identifica docs afetados
for file in changed_files:
    doc_path = f"docs/api/{file.replace('src/', 'src/').replace('.py', '.md')}"

    # 3. Marca para regeneração
    docs_to_regenerate.append(doc_path)

# 4. Após apply (queue vazia), regenera docs
if queue_empty:
    generator.regenerate(docs_to_regenerate)
    generator.update_index_json()
    generator.update_index_md()
```

**Logs de rastreamento em `generated_documentation`:**

```sql
-- Após gerar cada doc
INSERT INTO generated_documentation (
    file_path,           -- src/scanner.py
    doc_path,            -- docs/api/src/scanner.md
    doc_type,            -- 'module_complete'
    source_hash,         -- hash de src/scanner.py
    content_hash,        -- hash de docs/api/src/scanner.md
    metadata             -- JSON com front matter
) VALUES (?, ?, ?, ?, ?, ?);
```

**Próximo sync:**
```python
# Compara source_hash
if current_hash(src/scanner.py) != stored_source_hash:
    regenerate(docs/api/src/scanner.md)
```

---

## 🎯 RESUMO EXECUTIVO

### Arquivos Criados:
1. ✅ **6 arquivos raiz** (readme, index, architecture, glossary, whereiwas, index.json)
2. ✅ **1 arquivo por módulo** em `docs/api/` (espelha src/)
3. ✅ **Conteúdo completo**: técnico (API) + conceitual (purpose, deps, I/O) em um só arquivo

### RAG/IA Requirements:
1. ✅ **index.json** - Grafo completo (módulos, classes, dependências, entry points)
2. ✅ **Front matter YAML** - Metadados em cada .md para semantic search
3. ✅ **Estrutura fixa** - Seções padronizadas para parsing fácil
4. ✅ **Executive summary** - Contexto rápido em readme.md

### Automação:
1. ✅ **Só gera quando queue vazia** (todos os markers processados)
2. ✅ **Change detection** - Regenera só docs de arquivos alterados
3. ✅ **Tracking** - Usa `generated_documentation` table

### Esquecer:
1. ❌ Diataxis (tutorials/how-to/explanation)
2. ❌ MkDocs / sites estáticos
3. ❌ reference/ e modules/ separados