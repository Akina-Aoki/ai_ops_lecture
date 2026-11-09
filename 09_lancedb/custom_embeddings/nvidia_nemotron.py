"""nvidia_nemotron.py - a CUSTOM embedding function for LanceDB that calls the NVIDIA API.

Why this file exists
--------------------
An *embedding* turns a piece of text into a list of numbers (a "vector"), so a computer can
compare texts by MEANING. LanceDB ships with ready-made embedding providers (Cohere,
sentence-transformers, OpenAI ...) but NOT with NVIDIA Nemotron. So we write our own small
class and "register" it, and LanceDB can then use it like any built-in provider.

Role in the project
-------------------
This file is a "leaf": it is used by a notebook and uses nothing else of ours.

    lancedb_embeddings.ipynb
        |  from custom_embeddings.nvidia_nemotron import NvidiaNemotronEmbedding
        |  get_registry().get("nvidia-nemotron").create()
        v
    nvidia_nemotron.py   --->   NVIDIA API (https://integrate.api.nvidia.com/v1)
        ^
        |  reads NVIDIA_API from the .env file

What happens when this file is imported (top to bottom)
-------------------------------------------------------
1. `load_dotenv()` reads the `.env` file so `NVIDIA_API` is available.
2. `client` is created. If NVIDIA_API is missing the OpenAI library raises an error right here,
   at import time, before any embedding is requested.
3. The `@get_registry().register("nvidia-nemotron")` decorator runs and adds the class to
   LanceDB's registry under the name "nvidia-nemotron". Importing the file is what makes
   `get_registry().get("nvidia-nemotron")` work in the notebook.

How LanceDB uses the class (two directions)
-------------------------------------------
    table.add(df)              -> LanceDB calls compute_source_embeddings(texts)
                                  -> input_type="passage"  (the documents we store)
    table.search("some text")  -> LanceDB calls compute_query_embeddings(query)
                                  -> input_type="query"    (what the user types)

Retrieval models like Nemotron embed a *document* and a *question* slightly differently, so we
must tell the API which one it is getting. That is the only reason there are two methods.
"""

import os
from dotenv import load_dotenv
from openai import OpenAI  # the NVIDIA API speaks the OpenAI protocol, so we reuse this client
from lancedb.embeddings import TextEmbeddingFunction, get_registry
import numpy as np

# Read variables from the .env file (e.g. NVIDIA_API=nvapi-...) into the environment.
load_dotenv()

# One shared connection to the NVIDIA API (same trick as model.py in lectures 01-08:
# the OpenAI client with a different base_url).
client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=os.getenv("NVIDIA_API"),  # the key lives in .env, never in the code
    max_retries=3,  # retry a failed request up to 3 times
    timeout=60.0,  # give up after 60 seconds
)


# The decorator adds this class to LanceDB's registry under the name "nvidia-nemotron".
# After that, `get_registry().get("nvidia-nemotron").create()` builds an instance.
@get_registry().register("nvidia-nemotron")
class NvidiaNemotronEmbedding(TextEmbeddingFunction):
    """LanceDB embedding function backed by an NVIDIA Nemotron embedding model.

    We extend `TextEmbeddingFunction`, LanceDB's base class for text embedders. It requires us to
    say how long the vectors are (`ndims`) and how to produce them (`generate_embeddings`).
    The two `compute_*` methods are what LanceDB actually calls (see the module docstring).
    """

    # Settings of the class. They can be changed when creating it,
    # e.g. get_registry().get("nvidia-nemotron").create(model="another-model").
    model: str = "nvidia/nemotron-3.5-embed-8b"
    dimensions: int = 4096  # length of every vector the model returns

    def ndims(self) -> int:
        """Tell LanceDB how many numbers each vector has.

        LanceDB needs this to build the table column `Vector(4096)`.
        It must match the real size returned by the model.
        """
        return self.dimensions

    def _embed_one(self, text: str, input_type: str) -> np.ndarray:
        """Embed ONE text by calling the NVIDIA API. Returns a numpy array of float32.

        `input_type` is "passage" (a stored document) or "query" (a search question).
        It is not part of the standard OpenAI API, so we pass it through `extra_body`.
        """
        response = client.embeddings.create(
            model=self.model,
            input=[text],  # the API accepts a list; we send one text per call
            extra_body={"input_type": input_type},
        )
        # response.data[0].embedding is a plain Python list of floats.
        # LanceDB stores float32, so we convert it to a numpy float32 array.
        vector = np.asarray(response.data[0].embedding, dtype=np.float32)
        return vector

    def generate_embeddings(self, texts, *args, **kwargs):
        """Embed many texts as *passages* (documents). Required by the base class.

        `sanitize_input` (from the base class) makes sure `texts` is a clean list of strings.
        Note: one API call per text. Simple, but slow for big tables.
        """
        texts = self.sanitize_input(texts)
        return [self._embed_one(text, input_type="passage") for text in texts]

    def compute_source_embeddings(self, texts, *args, **kwargs):
        """Called by LanceDB when we ADD rows (`table.add(...)`): embed the stored documents."""
        return self.generate_embeddings(texts)

    def compute_query_embeddings(self, query, *args, **kwargs):
        """Called by LanceDB when we SEARCH (`table.search("text")`): embed the user's question.

        Same as above but with input_type="query", so query and documents are embedded in a way
        that makes them comparable.
        """
        texts = self.sanitize_input(query)
        return [self._embed_one(text, input_type="query") for text in texts]
