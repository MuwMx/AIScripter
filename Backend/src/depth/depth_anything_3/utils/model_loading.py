













"""
Model loading and state dict conversion utilities.
"""

from typing import Dict, Tuple
import torch

from depth_anything_3.utils.logger import logger


def convert_general_state_dict(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """
    Convert general model state dict to match current model architecture.

    Args:
        state_dict: Original state dictionary

    Returns:
        Converted state dictionary
    """
    
    state_dict = {k.replace("module.", "model."): v for k, v in state_dict.items()}
    state_dict = {k.replace(".net.", ".backbone."): v for k, v in state_dict.items()}

    
    if "model.backbone.pretrained.camera_token" in state_dict:
        del state_dict["model.backbone.pretrained.camera_token"]

    
    state_dict = {
        k.replace(".camera_token_extra", ".camera_token"): v for k, v in state_dict.items()
    }

    
    state_dict = {
        k.replace("model.all_heads.camera_cond_head", "model.cam_enc"): v
        for k, v in state_dict.items()
    }
    state_dict = {
        k.replace("model.all_heads.camera_head", "model.cam_dec"): v for k, v in state_dict.items()
    }
    state_dict = {k.replace(".more_mlps.", ".backbone."): v for k, v in state_dict.items()}
    state_dict = {k.replace(".fc_rot.", ".fc_qvec."): v for k, v in state_dict.items()}
    state_dict = {
        k.replace("model.all_heads.head", "model.head"): v for k, v in state_dict.items()
    }

    
    state_dict = {
        k.replace("output_conv2_additional.sky_mask", "sky_output_conv2"): v
        for k, v in state_dict.items()
    }
    state_dict = {k.replace("_ray.", "_aux."): v for k, v in state_dict.items()}

    
    state_dict = {k.replace("gaussian_param_head.", "gs_head."): v for k, v in state_dict.items()}

    return state_dict


def convert_metric_state_dict(state_dict: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
    """
    Convert metric model state dict to match current model architecture.

    Args:
        state_dict: Original metric state dictionary

    Returns:
        Converted state dictionary
    """
    
    state_dict = {"module." + k: v for k, v in state_dict.items()}
    return convert_general_state_dict(state_dict)


def load_pretrained_weights(model, model_path: str, is_metric: bool = False) -> Tuple[list, list]:
    """
    Load pretrained weights for a single model.

    Args:
        model: Model instance to load weights into
        model_path: Path to the pretrained weights
        is_metric: Whether this is a metric model

    Returns:
        Tuple of (missed_keys, unexpected_keys)
    """
    state_dict = torch.load(model_path, map_location="cpu")

    if is_metric:
        state_dict = convert_metric_state_dict(state_dict)
    else:
        state_dict = convert_general_state_dict(state_dict)

    missed, unexpected = model.load_state_dict(state_dict, strict=False)
    del state_dict
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
    logger.info("Missed keys:", missed)
    logger.info("Unexpected keys:", unexpected)

    return missed, unexpected


def load_pretrained_nested_weights(
    model, main_model_path: str, metric_model_path: str
) -> Tuple[list, list]:
    """
    Load pretrained weights for a nested model with both main and metric branches.

    Args:
        model: Nested model instance
        main_model_path: Path to main model weights
        metric_model_path: Path to metric model weights

    Returns:
        Tuple of (missed_keys, unexpected_keys)
    """
    
    state_dict0 = torch.load(main_model_path, map_location="cpu")
    state_dict0 = convert_general_state_dict(state_dict0)
    state_dict0 = {k.replace("model.", "model.da3."): v for k, v in state_dict0.items()}

    
    state_dict1 = torch.load(metric_model_path, map_location="cpu")
    state_dict1 = convert_metric_state_dict(state_dict1)
    state_dict1 = {k.replace("model.", "model.da3_metric."): v for k, v in state_dict1.items()}

    
    combined_state_dict = state_dict0.copy()
    combined_state_dict.update(state_dict1)
    del state_dict0
    del state_dict1

    missed, unexpected = model.load_state_dict(combined_state_dict, strict=False)
    del combined_state_dict
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    print("Missed keys:", missed)
    print("Unexpected keys:", unexpected)

    return missed, unexpected
