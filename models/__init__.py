from .lr_scheduler import *
from .nn import *

from . import lr_scheduler
from . import nn


def get_model(**override):
    import config
    options = dict(
        in_channels=config.IN_CHANNELS,
        out_channels=1,
        channels=config.CHANNELS,
        num_layers=config.NUM_LAYERS,
        dropout_rate=config.DROPOUT_RATE,
        activation=config.ACTIVATION
    )
    options.update(override)
    return MLP(**options)


def get_optimizer_from_config(model_or_parameters):
    from collections import Iterable
    from torch.nn import Module
    import torch.optim as optim
    import config
    if isinstance(model_or_parameters, Module):
        parameters = model_or_parameters.parameters()
    elif isinstance(model_or_parameters, list):
        parameters = model_or_parameters
    elif isinstance(model_or_parameters, Iterable):
        parameters = list(model_or_parameters)
    else:
        raise TypeError(model_or_parameters)
    return getattr(optim, config.OPTIMIZER)(parameters, **config.OPTIMIZER_OPTIONS)


def get_lr_scheduler_from_config(optimizer):
    import config
    import torch.optim.lr_scheduler as scheduler
    from . import lr_scheduler as custom_scheduler
    cls = getattr(scheduler, config.LR_SCHEDULER, getattr(custom_scheduler, config.LR_SCHEDULER, None))
    if cls is None:
        raise TypeError("Invalid LR_SCHEDULER name from config: %s" % config.LR_SCHEDULER)
    return cls(optimizer, **config.LR_SCHEDULER_OPTIONS)
