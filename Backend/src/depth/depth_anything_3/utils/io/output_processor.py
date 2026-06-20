













"""
Output processor for Depth Anything 3.

This module handles model output processing, including tensor-to-numpy conversion,
batch dimension removal, and Prediction object creation.
"""

from __future__ import annotations

import numpy as np
import torch

from depth_anything_3.specs import Prediction
from src.depth.attr_dict import AttrDict as AddictDict



class OutputProcessor:
    """
    Output processor for converting model outputs to Prediction objects.

    Handles tensor-to-numpy conversion, batch dimension removal,
    and creates structured Prediction objects with proper data types.
    """

    def __init__(self) -> None:
        """Initialize the output processor."""

    def __call__(self, model_output: dict[str, torch.Tensor]) -> Prediction:
        """
        Convert model output to Prediction object.

        Args:
            model_output: Model output dictionary containing depth, conf, extrinsics, intrinsics
                         Expected shapes: depth (B, N, 1, H, W), conf (B, N, 1, H, W),
                         extrinsics (B, N, 4, 4), intrinsics (B, N, 3, 3)

        Returns:
            Prediction: Object containing depth estimation results with shapes:
                       depth (N, H, W), conf (N, H, W), extrinsics (N, 4, 4), intrinsics (N, 3, 3)
        """

        depth = self._extract_depth(model_output)
        conf = self._extract_conf(model_output)
        extrinsics = self._extract_extrinsics(model_output)
        intrinsics = self._extract_intrinsics(model_output)
        sky = self._extract_sky(model_output)
        aux = self._extract_aux(model_output)
        gaussians = model_output.get("gaussians", None)
        scale_factor = model_output.get("scale_factor", None)

        return Prediction(
            depth=depth,
            sky=sky,
            conf=conf,
            extrinsics=extrinsics,
            intrinsics=intrinsics,
            is_metric=getattr(model_output, "is_metric", 0),
            gaussians=gaussians,
            aux=aux,
            scale_factor=scale_factor,
        )

    def _extract_depth(self, model_output: dict[str, torch.Tensor]) -> np.ndarray:
        """
        Extract depth tensor from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Depth array with shape (N, H, W)
        """
        depth = model_output["depth"].squeeze(0).squeeze(-1).cpu().numpy()
        return depth

    def _extract_conf(self, model_output: dict[str, torch.Tensor]) -> np.ndarray | None:
        """
        Extract confidence tensor from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Confidence array with shape (N, H, W) or None
        """
        conf = model_output.get("depth_conf", None)
        if conf is not None:
            conf = conf.squeeze(0).cpu().numpy()
        return conf

    def _extract_extrinsics(self, model_output: dict[str, torch.Tensor]) -> np.ndarray | None:
        """
        Extract extrinsics tensor from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Extrinsics array with shape (N, 4, 4) or None
        """
        extrinsics = model_output.get("extrinsics", None)
        if extrinsics is not None:
            extrinsics = extrinsics.squeeze(0).cpu().numpy()
        return extrinsics

    def _extract_intrinsics(self, model_output: dict[str, torch.Tensor]) -> np.ndarray | None:
        """
        Extract intrinsics tensor from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Intrinsics array with shape (N, 3, 3) or None
        """
        intrinsics = model_output.get("intrinsics", None)
        if intrinsics is not None:
            intrinsics = intrinsics.squeeze(0).cpu().numpy()
        return intrinsics

    def _extract_sky(self, model_output: dict[str, torch.Tensor]) -> np.ndarray | None:
        """
        Extract sky tensor from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Sky mask array with shape (N, H, W) or None
        """
        sky = model_output.get("sky", None)
        if sky is not None:
            sky = sky.squeeze(0).cpu().numpy() >= 0.5
        return sky

    def _extract_aux(self, model_output: dict[str, torch.Tensor]) -> AddictDict:
        """
        Extract auxiliary data from model output and convert to numpy.

        Args:
            model_output: Model output dictionary

        Returns:
            Dictionary containing auxiliary data
        """
        aux = model_output.get("aux", None)
        ret = AddictDict()
        if aux is not None:
            for k in aux.keys():
                if isinstance(aux[k], torch.Tensor):
                    ret[k] = aux[k].squeeze(0).cpu().numpy()
                else:
                    ret[k] = aux[k]
        return ret



OutputAdapter = OutputProcessor
