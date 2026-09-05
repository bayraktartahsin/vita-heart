"""Vita Heart agents: the fleet that reads boxes, checks safety, coaches and writes.

Every model call goes through Amazon Bedrock. Model choice is measured, not
assumed (docs/DECISIONS.md): Nova Lite reads labels (fast, vision), Claude
Sonnet 4.5 writes the few sentences a person reads, Nova Pro is the fallback.
"""
