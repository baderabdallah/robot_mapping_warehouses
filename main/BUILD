load("@rules_cc//cc:defs.bzl", "cc_binary", "cc_library")
load("@python_deps//:requirements.bzl", "requirement")



cc_library(
    name = "parse_data",
    srcs = ["parse_data.cpp"],
    hdrs = ["parse_data.h"],
    deps = [
        "//nohlman:nohlman",
        "//object_tracking/data_types:data_types",
    ],
)

cc_library(
    name = "writers",
    srcs = ["writers.cpp"],
    hdrs = ["writers.h"],
    deps = [
        "//nohlman:nohlman",
        "//object_tracking/data_types:data_types",
    ],
)

cc_binary(
    name = "main",
    srcs = ["main.cpp"],
    deps = [
        ":parse_data",
        ":writers",
        "//object_tracking:object_tracking",
        "//object_tracking/data_types:data_types",
        "//nohlman:nohlman",
        "//interpolation:interpolation",
        "@com_google_googletest//:gtest_main",
    ],
)

