# Vendored code

`rxnorm.py`, `fda.py` and `cabinet.py` come from VitaCabinet
(https://github.com/bayraktartahsin/vitacabinet, Apache-2.0, same author),
built for the AWS "Agents for Humans" hackathon in August 2026. They are copied
rather than imported so that every line that names a medicine is in this repo
for review. Changes here: module paths only.

What they do: RxNorm identification with a round-trip name guard (the fuzzy
matcher is not trusted unless the name it returns shares words with the label),
openFDA live-recall lookup with lot numbers carried, and a fact store where every
fact carries its source and decays to zero confidence over a source-specific
horizon. Everything else in this repository is new for Build, Ship, Shape.
