# AXLE — Axis-guided Lived Experience elicitation

Code, data and analysis for *Activating the Annotator: Operationalising Lived Experience in Data Annotation*.

AXLE is a pre-annotation stage in which a scenario vignette anchors a short, axis-guided
conversation that is synthesised into a first-person micro-narrative and returned to the
annotator before labelling begins. This repository contains the instrument, the 30-item
ambiguous hate speech corpus, the annotation data from a 2×2 between-subjects study
(104 annotators, 1,040 annotations), and scripts reproducing every table and figure in the paper.

---
## Ethics and licensing

The study was approved by the authors' institutional research ethics board. Participants gave
informed consent, were told the study concerned annotation of potentially offensive social media
content, and could withdraw at any time. Compensation was above platform minimum, prorated by
condition. Prolific IDs are used only for payment and are removed from the released data;
narratives and rationales were reviewed for identifying detail before release. 

The elicitation stage invites disclosure of experiences of marginalisation and is a real
affective demand on workers. Anyone deploying it at scale should treat that emotional labour
as a cost borne by workers, not an externality. Mitigations implemented here: a hard five-turn
cap, a wind-down turn, and no follow-up pressure on thin answers about sensitive axes.

An instrument that reliably shifts harm judgements could be used to manufacture a desired label
distribution rather than surface one. The entropy result offers partial protection, since
elicitation widens rather than narrows the distribution, but the risk applies to any framing
intervention placed upstream of labelling.

Code is released under the MIT License. Data and the item corpus are released under CC BY 4.0
for research use; the corpus is synthetic and should not be treated as naturally occurring text.

## Citation

Anonymised for review. A `CITATION.cff` will be added on de-anonymisation.
