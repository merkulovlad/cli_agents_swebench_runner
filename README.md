# SWE-bench Code Model Performance Monitor

## Purpose

This project provides an empirical framework for measuring the performance of code-focused agents like Claude Code, Codex, Gemini, and local/custom agents on real-world software engineering tasks. It was built to provide objective, reproducible metrics that allow users to assess these tools for themselves, rather than relying on anecdotal reports or marketing claims.

The SWE-bench benchmark presents the model with actual GitHub issues from popular open-source projects and measures its ability to generate patches that successfully resolve these issues. This provides a concrete, measurable answer to the question: "How well do these code models actually perform on real software engineering tasks?"

> **Platform support:** The tools in this repository run on Linux, macOS, and Windows (including WSL). Replace `python` with `python3` on Unix-like systems or `py` on Windows if needed.

## Acknowledgements

This project started from the original work by [jimmc414](https://github.com/jimmc414/claudecode_gemini_and_codex_swebench) and is now maintained as an independent extension.

Changes:
- Added dataset alias support.
- Added a local/custom agent backend.
- Added API/proxy configuration support.
- Improved runtime logging and timeout configuration.
- Fixed partial-run evaluation scoring.

## Getting Started in 5 Minutes

```bash
# Assuming you have Python, a code model CLI, and Docker installed:
git clone https://github.com/merkulovlad/cli_agents_swebench_runner.git
cd cli_agents_swebench_runner
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python swe_bench.py run --limit 1  # Run your first test (~10 min)
python swe_bench.py scores         # See your results
```

For detailed setup instructions, see [Prerequisites](#prerequisites) and [Installation](#installation) below.

## Quick Start (After Installation)

```bash
# 1. Run your first test (1 instance, ~10 minutes)
python swe_bench.py run --limit 1               # Claude Code (default)
python swe_bench.py run --limit 1 --backend codex  # Codex
python swe_bench.py run --limit 1 --backend gemini # Gemini
python swe_bench.py run --limit 1 --backend local --agent-command "supercode" # Local agent

# 2. Check your results
python swe_bench.py scores

# 3. Try a larger test when ready (10 instances, ~2 hours)
python swe_bench.py quick
```


## Prerequisites

Before starting, ensure you have:

1. **Python 3.8 or newer**
   ```bash
   python --version  # or python3/py --version
   ```

2. **Claude Code, Codex, Gemini CLI, or a local/custom agent installed**
   ```bash
   # Claude Code
   claude --version  # Should work without errors
   # Codex
   codex --version   # Should work without errors
   # Gemini
   gemini --version  # Should work without errors
   # If not logged in, run the relevant CLI
   ```

   The CLIs use their default authentication unless API environment variables are set. You can override API keys and endpoints before running the benchmark:
   ```bash
   # Claude Code
   export ANTHROPIC_API_KEY="your-api-key"
   export ANTHROPIC_BASE_URL="https://api.anthropic.com"

   # Codex
   export OPENAI_API_KEY="your-api-key"
   export OPENAI_BASE_URL="https://api.openai.com/v1"

   # Gemini
   export GEMINI_API_KEY="your-api-key"
   # GOOGLE_API_KEY is also respected if already set
   ```

   For convenience, this project also maps `api` or `API` to the selected backend's API key when that backend's key is not already set:
   ```bash
   export api="your-api-key"
   # or
   export API="your-api-key"
   ```

   Local proxy example for Claude-compatible endpoints:
   ```bash
   ANTHROPIC_BASE_URL="http://localhost:8082" \
   ANTHROPIC_API_KEY="any-value" \
   python run_benchmark_with_eval.py \
     --backend claude \
     --model claude-3-5-sonnet-20241022 \
     --dataset lite \
     --limit 10
   ```

3. **Docker installed and running**
   ```bash
   docker --version  # Should show version
   docker ps        # Should work without "daemon not running" error
   ```
   - Needs ~50GB free disk space for images
   - 16GB+ RAM recommended
   - For Mac/Windows: Increase Docker Desktop memory to 8GB+
   
   **Don't have Docker?** The easiest way is to ask Claude Code to set it up:
   ```bash
   claude  # Open Claude Code
   # Then ask: "Please help me install Docker on my system"
   ```
   Or see [Manual Docker Setup](#docker-setup) below.

## Installation

```bash
# 1. Clone this repository
git clone <repository-url>
cd cli_agents_swebench_runner

# 2. Install all Python dependencies (includes swebench)
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

# 3. Verify everything is working
python swe_bench.py list-models               # Claude models
python swe_bench.py list-models --backend codex  # Codex models
python swe_bench.py list-models --backend gemini # Gemini models

# Optional: Quick test to verify full setup
python swe_bench.py run --limit 1 --no-eval  # Test without Docker (2-5 min)
python swe_bench.py run --limit 1            # Full test with Docker (10-15 min)
```

### Troubleshooting Setup

If you get errors:

- **"Claude CLI not found"**: Install from https://claude.ai/download
- **"Codex CLI not found"**: Ensure `codex` is installed and in your PATH
- **"Gemini CLI not found"**: Ensure `gemini` is installed and in your PATH
- **"Docker daemon not running"**: Start Docker Desktop or `sudo systemctl start docker`
- **"swebench not found"**: Run `pip install swebench`
- **Out of memory**: Increase Docker memory in Docker Desktop settings
- **Permission denied (Docker)**: Add yourself to docker group: `sudo usermod -aG docker $USER` then logout/login

## Command Reference

### Main Tool: `swe_bench.py`

The unified tool provides all functionality through a single entry point:

```bash
# Default: Run full 300-instance benchmark
python swe_bench.py

# Quick commands
python swe_bench.py quick          # 10 instances with evaluation
python swe_bench.py full           # 300 instances with evaluation
python swe_bench.py scores         # View scores and statistics
python swe_bench.py list-models    # Show available models (Claude by default)
python swe_bench.py list-models --backend codex  # Show Codex models
python swe_bench.py list-models --backend gemini # Show Gemini models
python swe_bench.py list-datasets  # Show available dataset aliases
```

### Running Benchmarks

```bash
# Basic runs with different sizes
python swe_bench.py run --quick                    # 10 instances
python swe_bench.py run --standard                 # 50 instances
python swe_bench.py run --full                     # 300 instances
python swe_bench.py run --limit 25                 # Custom count

# Model selection (September 2025 models)
python swe_bench.py run --model opus-4.1 --quick   # Latest Opus
python swe_bench.py run --model sonnet-3.7 --limit 20
python swe_bench.py run --model best --quick       # Best performance alias

# Performance options
python swe_bench.py run --quick --no-eval          # Skip Docker evaluation
python swe_bench.py run --limit 20 --max-workers 4 # More parallel containers
python swe_bench.py run --limit 10 --inference-timeout 21600 # 6 hour generation timeout

# Local agent backend
python swe_bench.py run --backend local --agent-command "supercode" --limit 5
python swe_bench.py run --backend local --agent-command "supercode --config swebench.yaml" --agent-timeout 900 --limit 5

# Dataset selection
python swe_bench.py run --dataset lite --limit 10
python swe_bench.py run --dataset verified --limit 10
python swe_bench.py run --dataset full --limit 10
python swe_bench.py run --dataset multimodal --limit 10
python swe_bench.py run --dataset multilingual --limit 10
python swe_bench.py run --dataset princeton-nlp/SWE-bench_Lite --limit 10
```

The local backend runs the agent headlessly as
`supercode -p "<prompt>" -skip-permissions`. Session logs written under a
hidden agent directory in the checkout are preserved in
`results/<instance_id>/sessions/`.

Supported aliases are `lite`, `verified`, `full`, `multimodal`, and `multilingual`. You can also pass a full Hugging Face dataset ID.

### Running Specific Test Instances

When establishing a baseline or debugging specific issues, you can run SWE-bench against individual test instances:

```bash
# Using code_swe_agent.py directly (patch generation only)
python code_swe_agent.py --instance_id django__django-11133

# Specify backend explicitly
python code_swe_agent.py --instance_id django__django-11133 --backend codex

# With full SWE-bench dataset instead of Lite
python code_swe_agent.py --instance_id django__django-11133 --dataset_name princeton-nlp/SWE-bench

# With specific model for baseline comparison
python code_swe_agent.py --instance_id django__django-11133 --model opus-4.1

# Finding available instance IDs
python -c "from datasets import load_dataset; ds = load_dataset('princeton-nlp/SWE-bench_Lite', split='test'); print('\\n'.join([d['instance_id'] for d in ds][:20]))"
```

**Use Cases for Single Instance Testing:**
- Establishing performance baselines for specific problem types
- Debugging Claude Code's approach to particular challenges
- Comparing model performance on identical problems
- Validating fixes after prompt or model updates

**Note:** Instance IDs follow the format `<repo>__<repo>-<issue_number>` (e.g., `django__django-11133`, `sympy__sympy-20154`)

### Evaluating Past Runs

```bash
# Interactive selection menu
python swe_bench.py eval --interactive

# Specific file
python swe_bench.py eval --file predictions_20250902_163415.jsonl

# By date
python swe_bench.py eval --date 2025-09-02
python swe_bench.py eval --date-range 2025-09-01 2025-09-03

# Recent runs
python swe_bench.py eval --last 5

# Preview without running
python swe_bench.py eval --last 3 --dry-run
```

Partial prediction files are scored against submitted/completed instances, not the full dataset size. For example, if 9 predictions are submitted and 5 resolve, the evaluation score is `5/9`, not `5/300`.

### Viewing Scores

```bash
# Basic score view
python swe_bench.py scores

# With statistics and analysis
python swe_bench.py scores --stats --trends

# Filter results
python swe_bench.py scores --filter evaluated      # Only evaluated runs
python swe_bench.py scores --filter pending        # Only pending evaluation

# Export to CSV
python swe_bench.py scores --export results.csv

# Recent entries
python swe_bench.py scores --last 10
```

## Model Selection

### Available Models (September 2025)

```bash
# View all available models and their expected performance
python swe_bench.py list-models
```

**Opus Models** (Most Capable):
- `opus-4.1`: Latest, 30-40% expected score
- `opus-4.0`: Previous version, 25-35% expected score

**Sonnet Models** (Balanced):
- `sonnet-4`: New generation, 20-30% expected score
- `sonnet-3.7`: Latest 3.x, 18-25% expected score
- `sonnet-3.6`: Solid performance, 15-22% expected score
- `sonnet-3.5`: Fast/efficient, 12-20% expected score

**Aliases**:
- `best`: Maps to opus-4.1
- `balanced`: Maps to sonnet-3.7
- `fast`: Maps to sonnet-3.5

You can also use any model name accepted by Claude's `/model` command, including experimental or future models not yet in the registry.

## Understanding Scores

### Two Types of Scores

1. **Generation Score**: Percentage of instances where a patch was created (misleading)
2. **Evaluation Score**: Percentage of instances where the patch actually fixes the issue (real score)

Only the evaluation score matters. A 100% generation score with 20% evaluation score means Claude Code created patches for all issues but only 20% actually worked.

### Expected Performance Ranges

Based on empirical testing with SWE-bench:

| Score Range | Performance Level | What It Means |
|------------|------------------|---------------|
| 0-5% | Poor | Patches rarely work, significant issues |
| 5-10% | Below Average | Some success but needs improvement |
| 10-15% | Average | Decent performance for an AI system |
| 15-20% | Good | Solid performance, useful for real work |
| 20-25% | Very Good | Strong performance, competitive |
| 25-30% | Excellent | Top-tier performance |
| 30%+ | Outstanding | Exceptional, rare to achieve |

### Time Estimates

| Test Size | Instances | Generation | Evaluation | Total Time |
|-----------|-----------|------------|------------|------------|
| Quick | 10 | ~20-30 min | ~30-50 min | ~1-2 hours |
| Standard | 50 | ~2-3 hours | ~3-5 hours | ~5-8 hours |
| Full | 300 | ~12-15 hours | ~20-30 hours | ~35-45 hours |

## Project Structure

```
cli_agents_swebench_runner/
├── swe_bench.py              # Main unified tool (all commands)
├── code_swe_agent.py         # Core agent for Claude Code, Codex, Gemini, or local agents
├── USAGE.md                  # Detailed command usage guide
├── benchmark_scores.log      # Results log (JSON lines format)
├── requirements.txt          # Python dependencies
│
├── utils/                    # Core utilities
│   ├── claude_interface.py  # Claude Code CLI interface
│   ├── codex_interface.py   # Codex CLI interface
│   ├── gemini_interface.py  # Gemini CLI interface
│   ├── local_interface.py   # Local/custom agent command interface
│   ├── prompt_formatter.py  # Formats issues into prompts
│   ├── patch_extractor.py   # Extracts patches from responses
│   └── model_registry.py    # Model definitions and aliases
│
├── prompts/                  # Prompt templates
│   ├── swe_bench_prompt.txt # Default prompt
│   ├── chain_of_thought_prompt.txt
│   └── react_style_prompt.txt
│
├── predictions/              # Generated predictions (JSONL, ignored except .gitkeep)
├── results/                  # Detailed model outputs (ignored except .gitkeep)
└── evaluation_results/       # Docker evaluation results (ignored except .gitkeep)
```

## Verification Checklist

Use this checklist to verify Claude Code is working properly:

```bash
# 1. Test setup (should list models)
python swe_bench.py list-models

# 2. Single instance test (5-10 minutes)
python swe_bench.py run --limit 1 --no-eval

# 3. Quick test with evaluation (1-2 hours)
python swe_bench.py quick

# 4. Check scores (should show real evaluation scores)
python swe_bench.py scores

# 5. If scores look good, try larger test
python swe_bench.py run --standard  # 50 instances
```

## Troubleshooting

### Common Issues

**Claude CLI not found**
```bash
# Ensure claude is in PATH
which claude
# If not found, reinstall Claude Code or add to PATH
```

**Docker permission denied**
```bash
# Add user to docker group
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

**Out of memory during evaluation**
```bash
# Reduce parallel workers
python swe_bench.py run --quick --max-workers 1
```

**Evaluation times out**
- Some instances take longer to test
- Default timeout is 30 minutes per instance
- This is normal for complex codebases

**Low scores (0-5%)**
- This may be normal for certain models or datasets
- Try with a better model: `--model opus-4.1`
- Check that Claude Code is properly authenticated

### Log Files

- **benchmark_scores.log**: Main results log (JSON lines)
- **predictions/**: All generated patches
- **evaluation_results/**: Detailed Docker test results
- **results/**: Raw model outputs and preserved agent session logs for debugging

Each prediction and detailed task result includes `task_time_seconds`, measured
after repository setup. Benchmark summaries include `total_task_time` and
`average_task_time`, so repository cloning and checkout time are excluded.

## Docker Setup

If you don't have Docker installed, here's how to set it up manually:

### macOS
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop/
# Or use Homebrew:
brew install --cask docker

# Start Docker Desktop from Applications
# Increase memory to 8GB in Docker Desktop > Settings > Resources
```

### Ubuntu/Debian Linux
```bash
# Update packages and install prerequisites
sudo apt update
sudo apt install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo mkdir -p /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

# Set up repository
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group (avoids needing sudo)
sudo usermod -aG docker $USER
# Log out and back in for this to take effect

# Start Docker
sudo systemctl start docker
sudo systemctl enable docker

# Verify installation
docker run hello-world
```

### Windows
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop/

# Requirements:
# - Windows 10/11 64-bit with WSL 2
# - Enable virtualization in BIOS
# - Install WSL 2 first if needed:
wsl --install

# After installing Docker Desktop:
# - Increase memory to 8GB in Settings > Resources
# - Ensure WSL 2 backend is enabled
```

### Verify Docker is Ready
```bash
# Check Docker is installed
docker --version

# Check Docker daemon is running
docker ps

# Test Docker works
docker run hello-world
```


## License

This benchmarking framework is provided as-is for empirical evaluation purposes. SWE-bench is created by Princeton NLP. Claude Code is a product of Anthropic.
