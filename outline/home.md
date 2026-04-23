# Background

This repo is for a paper I am writing on a system I built, called ORCA.

I am trying to orchestrate a workflow for agents to assist me in writing the paper.

## Resources

Things to help understand paper scope. All paths relative to repo root

- /local/amr.md -- a summary of the AMR paper that was the motivation for this work
- /local/amr.pdf -- the actual AMR paper, full text. avoid reading to preserve context
- /local/orca.txt -- some notes on ORCA the system
- /local/orca_overview.pdf -- a brochure-level summary of ORCA. Abstract, some details outdated.
- /local/AGENTS.md -- some old agent instructions + discussion. Use for context. Do not take too seriously.

## File Structure

The latex entry point is main.tex. Includes all sections:

- tex/00-intro-gem.tex
- tex/00-intro.tex
- tex/01-bg-cla.tex
- tex/01-bg-gem.tex
- tex/01-bg.tex
- tex/02-chal.tex
- tex/03-design-cla.tex
- tex/03-design.tex
- tex/04-impl.tex
- tex/05-eval.tex
- tex/06-related.tex
- tex/07-concl.tex


Some older attempts at outlines here:
- tex/outline.tex
- tex/points.tex
- tex/text.tex
- tex/vscs_outline.tex

If any file contains the names cla or gem or gpt, that indicates the agent that created it.

Essentially the agent has proposed changes but I have not merged them or something.

- cla: claude
- gem: gemini
- gpt: GPT/Codex

## Paper Workflow

We want to have a scaffolding that allows us to think about the paper and iteratively perfect the text.

The scaffolding will promote tree-like thinking.

1. We want a paper-level outline in outline/main.md
2. This will inform section-level outlines in `outline/00-sec.tex`
3. These will inform the actual paper text

In addition, we may create some mechanisms for thoughts/fragments that have not been integrated yet. So the paper is essentially like the leaf level of an LSM tree that periodically gets compacted and we try to keep the outlines in sync.

## Writing Style

- We want dense, clinical, flowy narrative.
- We want to use the tree-based structure to stay focused.
- We like writing techniques such as BLUF (bottom line up front). The BLUFs should connect across paragraphs.
- Before every section/subsection, we want to have a quick outline in the actual tex that informs the content of each para.

```tex
% (Sx: subsections)
% S1: why is it important
% S2: what is being done now
% S3: what we want to do

% S1 outline:
% P1: XYZ
% P2: XYZ
```

## Other Notes

- I sometimes like to write out fast and loose language "competition is crap, our thing is amazing". This is obviously not the final language. It is the subtext we want to eventually convey via professional language. But we shouldn't worry about refining language until we are happy with the broader structure of a section.


- Be aware that LLMs are very hard to steer to produce the language you want. This structure is supposed to help the user constrain and guide the LLMs in their preferred direction. The idea is to create hybrid workflows between user and agents. These directions will evolve over time.
