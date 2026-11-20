"""RD Studio: serviço de vozes compartilhado para personagens, cenas e roteiro."""
from .core import Catalog, normalize_voice, resolve_voice, edge_parameters, capabilities, resolve_voice_config, make_voice_plan
__all__ = ['Catalog','normalize_voice','resolve_voice','edge_parameters','capabilities','resolve_voice_config','make_voice_plan']
