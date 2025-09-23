"""
Mock FlatBuffers schema for embedding.fbs
This provides a simplified implementation for the embedding schema.
"""

import flatbuffers
from enum import IntEnum
import numpy as np


class DistanceMetric(IntEnum):
    COSINE = 0
    EUCLIDEAN = 1
    DOT_PRODUCT = 2
    MANHATTAN = 3
    HAMMING = 4


class EmbeddingModel(IntEnum):
    UNKNOWN = 0
    OPENAI_ADA_002 = 1
    OPENAI_3_SMALL = 2
    OPENAI_3_LARGE = 3
    SENTENCE_TRANSFORMERS = 4
    HUGGINGFACE = 5
    CUSTOM = 255


class VectorMetadata:
    """Mock VectorMetadata class."""
    def __init__(self, model=0, dimension=0, distance_metric=0, created_at=0, 
                 model_version="", framework="", parameters=""):
        self.model = model
        self.dimension = dimension
        self.distance_metric = distance_metric
        self.created_at = created_at
        self.model_version = model_version
        self.framework = framework
        self.parameters = parameters


class Embedding:
    """Mock Embedding class."""
    def __init__(self, vector=None, metadata=None, asset_id="", chunk_index=0, confidence=1.0):
        self.vector = vector
        self.metadata = metadata
        self.asset_id = asset_id
        self.chunk_index = chunk_index
        self.confidence = confidence


class EmbeddingRoot:
    """Mock EmbeddingRoot class."""
    def __init__(self, single=None, is_collection=False):
        self.single = single
        self.is_collection = is_collection


def GetRootAs(data, offset=0):
    """Mock GetRootAs function."""
    # This is a simplified implementation
    # In a real FlatBuffers implementation, this would parse the binary data
    return EmbeddingRoot()


def CreateVectorMetadata(builder, model, dimension, distance_metric, created_at, 
                        model_version, framework, parameters):
    """Create a VectorMetadata object."""
    return VectorMetadata(model, dimension, distance_metric, created_at, 
                         model_version, framework, parameters)


def CreateEmbedding(builder, vector_data, metadata, asset_id, chunk_index, confidence):
    """Create an Embedding object."""
    return Embedding(vector_data, metadata, asset_id, chunk_index, confidence)


def CreateEmbeddingRoot(builder, single, is_collection):
    """Create an EmbeddingRoot object."""
    return EmbeddingRoot(single, is_collection)