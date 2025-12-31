"""
SpeciesNet (iNaturalist) Integration
Species classification model trained on iNaturalist dataset
Supports 5,000+ wildlife species

Copyright (c) 2025 Omar Miranda
SPDX-License-Identifier: Apache-2.0
"""

import torch
import torchvision.transforms as transforms
from PIL import Image
import io
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger()


class SpeciesNet:
    """Wrapper for SpeciesNet (iNaturalist) species classification model"""

    def __init__(
        self,
        model_path: str,
        taxonomy_path: str = None,
        confidence_threshold: float = 0.5,
        device: str = None
    ):
        """
        Initialize SpeciesNet model

        Args:
            model_path: Path to SpeciesNet PyTorch model file
            taxonomy_path: Path to JSON file with species taxonomy mapping
            confidence_threshold: Minimum confidence score for predictions
            device: Device to run inference on (cuda/cpu). Auto-detect if None.
        """
        self.confidence_threshold = confidence_threshold

        # Set device
        if device is None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = torch.device(device)

        logger.info(f"Loading SpeciesNet model from {model_path}")
        logger.info(f"Using device: {self.device}")

        try:
            # Load model
            self.model = torch.load(model_path, map_location=self.device)
            self.model.to(self.device)
            self.model.eval()

            logger.info("SpeciesNet model loaded successfully")

            # Load taxonomy mapping
            if taxonomy_path:
                with open(taxonomy_path, 'r') as f:
                    self.taxonomy = json.load(f)
                logger.info(f"Loaded taxonomy for {len(self.taxonomy)} species")
            else:
                self.taxonomy = {}

            # Image preprocessing transforms
            self.transforms = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])

        except Exception as e:
            logger.error(f"Failed to load SpeciesNet model: {str(e)}")
            raise

    def classify(self, image_bytes: bytes, top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Classify species in image

        Args:
            image_bytes: Image file as bytes (cropped to animal region)
            top_k: Number of top predictions to return

        Returns:
            List of top-k predictions, each containing:
                - scientific_name: Scientific name of species
                - common_name: Common name of species
                - confidence: Prediction confidence (0-1)
                - taxonomy: Taxonomic classification (if available)
        """
        try:
            # Load and preprocess image
            image = Image.open(io.BytesIO(image_bytes)).convert('RGB')
            image_tensor = self.transforms(image).unsqueeze(0).to(self.device)

            # Run inference
            with torch.no_grad():
                outputs = self.model(image_tensor)
                probabilities = torch.nn.functional.softmax(outputs, dim=1)

            # Get top-k predictions
            top_probs, top_indices = torch.topk(probabilities, k=top_k, dim=1)

            predictions = []
            for prob, idx in zip(top_probs[0], top_indices[0]):
                confidence = float(prob)
                class_id = int(idx)

                # Get species info from taxonomy
                species_info = self.taxonomy.get(str(class_id), {})

                prediction = {
                    'class_id': class_id,
                    'confidence': confidence,
                    'scientific_name': species_info.get('scientific_name', f'Unknown_{class_id}'),
                    'common_name': species_info.get('common_name', 'Unknown'),
                }

                # Add taxonomy if available
                if 'taxonomy' in species_info:
                    prediction['taxonomy'] = species_info['taxonomy']

                predictions.append(prediction)

            # Filter by confidence threshold
            predictions = [p for p in predictions if p['confidence'] >= self.confidence_threshold]

            if predictions:
                logger.info(
                    f"Top prediction: {predictions[0]['common_name']} "
                    f"({predictions[0]['confidence']:.2f})"
                )
            else:
                logger.warning(f"No predictions above threshold {self.confidence_threshold}")

            return predictions

        except Exception as e:
            logger.error(f"Error running SpeciesNet: {str(e)}", exc_info=True)
            raise

    def get_species_info(self, class_id: int) -> Dict[str, Any]:
        """Get full species information by class ID"""
        return self.taxonomy.get(str(class_id), {})

    def set_confidence_threshold(self, threshold: float):
        """Update confidence threshold"""
        self.confidence_threshold = threshold
        logger.info(f"Updated confidence threshold to {threshold}")


def create_taxonomy_mapping():
    """
    Helper function to create taxonomy mapping from iNaturalist data
    This should be run separately to generate the taxonomy JSON file
    """
    # Example taxonomy structure
    taxonomy_example = {
        "0": {
            "scientific_name": "Ursus arctos",
            "common_name": "Brown Bear",
            "taxonomy": {
                "kingdom": "Animalia",
                "phylum": "Chordata",
                "class": "Mammalia",
                "order": "Carnivora",
                "family": "Ursidae",
                "genus": "Ursus"
            },
            "conservation_status": "LC"
        },
        "1": {
            "scientific_name": "Canis lupus",
            "common_name": "Gray Wolf",
            "taxonomy": {
                "kingdom": "Animalia",
                "phylum": "Chordata",
                "class": "Mammalia",
                "order": "Carnivora",
                "family": "Canidae",
                "genus": "Canis"
            },
            "conservation_status": "LC"
        }
        # ... more species
    }

    return taxonomy_example
