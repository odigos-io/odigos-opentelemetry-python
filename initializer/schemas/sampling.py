"""Typed shapes for the head-sampling configuration sent by the Odigos OpAMP server.

Mirrors the Go schema in odigos/common/api/sampling (matchers_head.go, sampling.go).
All fields are `omitempty` on the Go side (except NoisyOperation.id), so every
key is treated as optional on the wire — hence `total=False` on every TypedDict.
"""

from typing import TypedDict


class HeadSamplingHttpServerOperationMatcher(TypedDict, total=False):
    route: str
    routePrefix: str
    method: str


class HeadSamplingHttpClientOperationMatcher(TypedDict, total=False):
    serverAddress: str
    templatedPath: str
    templatedPathPrefix: str
    method: str


class HeadSamplingOperationMatcher(TypedDict, total=False):
    httpServer: HeadSamplingHttpServerOperationMatcher
    httpClient: HeadSamplingHttpClientOperationMatcher


class NoisyOperation(TypedDict, total=False):
    id: str
    name: str
    disabled: bool
    operation: HeadSamplingOperationMatcher
    percentageAtMost: float


class HeadSamplingConfig(TypedDict, total=False):
    dryRun: bool
    noisyOperations: list[NoisyOperation]
