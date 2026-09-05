# alphaxiv MCP Setup (Auto-Install)

**On skill activation**, check whether the alphaxiv MCP server is available:

1. **Detect**: Try calling `mcp__alphaxiv__full_text_papers_search` with a trivial query. If the tool exists, alphaxiv is ready — skip to step 3.
2. **Auto-install** (if tools are missing): Run the following command to add alphaxiv globally:
   ```bash
   claude mcp add --transport http alphaxiv https://api.alphaxiv.org/mcp/v1 -s user
   ```
   Then inform the user: "alphaxiv MCP 已自動安裝。請重新啟動 Claude Code 以啟用 alphaxiv 工具，或在下次對話中自動生效。"
   **Note**: After installation, alphaxiv tools (`mcp__alphaxiv__*`) will be available in the next session.
3. **Ready**: Proceed with the workflow. Use alphaxiv tools as the **primary** paper search/retrieval method alongside `arxiv_registry.py`.

## alphaxiv MCP Tools Reference

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `mcp__alphaxiv__full_text_papers_search` | Keyword search (method names, benchmarks, authors) | Gate 0 discovery, per-section search, daily monitoring |
| `mcp__alphaxiv__embedding_similarity_search` | Semantic/conceptual search (2-3 sentence queries) | Finding related work, gap analysis, novelty check |
| `mcp__alphaxiv__agentic_paper_retrieval` | Autonomous multi-turn search for comprehensive coverage | Always call IN PARALLEL with the above two for maximum recall |
| `mcp__alphaxiv__get_paper_content` | Get paper text/AI-generated report from arXiv URL | Reading paper details, extracting methods/results |
| `mcp__alphaxiv__answer_pdf_queries` | Answer questions about specific PDFs | Cross-paper comparison, detail extraction, claim verification |
| `mcp__alphaxiv__read_files_from_github_repository` | Read paper's code repository | Codebase-grounded papers, reproducibility checks |

**Best practice**: For any literature search, call all three search tools in parallel (`full_text_papers_search` + `embedding_similarity_search` + `agentic_paper_retrieval`) to maximize recall. Each covers different blind spots.
