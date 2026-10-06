"""GUI experiment composition; numerical models remain in the native runners.

Delivery-profile variation selects another registered, source-bound input.
It is deliberately not passed to the native numerical override interface.
"""
from __future__ import annotations

from copy import deepcopy
import math

import pandas as pd

from . import model_adapter

PROFILE_PARAMETER = "h2_delivery_profile"


def sensitivity_parameter_choices(native_units, site):
    """Retain the existing study-specific numeric interface and add profiles.

    Uniform WACC is an archived base configuration for Namibia. The generic
    GUI has never offered it as a free replacement for country WACC rates.
    A constant market price is likewise not offered for the historical EU
    price contract, and the demand quantity override is EU-contract-only.
    """
    choices = {key: unit for key, unit in dict(native_units).items()
               if key not in ("baseline", "uniform_real_wacc_fraction")}
    if site.runner_kind == "eu":
        choices.pop("electricity_price_eur_per_mwh", None)
    else:
        choices.pop("h2_demand_multiplier", None)
    if len(site.profiles) > 1:
        choices[PROFILE_PARAMETER] = "registered_profile"
    return choices


def _unique(values, label):
    selected = list(values)
    if len(set(selected)) != len(selected):
        raise ValueError(f"Doppelte {label} sind nicht zulässig.")
    return selected


def oat_profile_scope(base_profiles, scenarios, variants=(), profile_levels=(),
                      *, compare_solvers=False):
    """Return the visible OAT count without reading inputs or starting a model."""
    bases = _unique(base_profiles, "Basis-Lieferprofile")
    scenario_ids = _unique(scenarios, "Szenarien")
    levels = _unique(profile_levels, "Profilstufen")
    if not bases or not scenario_ids:
        raise ValueError("Mindestens ein Basis-Lieferprofil und ein Szenario wählen.")
    numeric = list(variants)
    if any(item.get("parameter") == PROFILE_PARAMETER for item in numeric):
        raise ValueError("Kategorische Lieferprofile separat als Profilstufen übergeben.")
    if not numeric and not levels:
        raise ValueError("Mindestens einen Sensitivitätsparameter mit Stufen wählen.")
    extras = [profile for profile in levels if profile not in bases]
    if not numeric and len(set(bases + levels)) < 2:
        raise ValueError("Ein Lieferprofilvergleich benötigt mindestens zwei verschiedene Profile.")
    return {
        "base_profiles": bases, "scenarios": scenario_ids,
        "variants": deepcopy(numeric), "profile_levels": levels,
        "profile_only_levels": extras, "compare_solvers": bool(compare_solvers),
        "optimization_count": (len(bases) * (1 + len(numeric)) + len(extras))
                              * len(scenario_ids) * (2 if compare_solvers else 1),
        "numeric_variants_crossed_with_profile_levels": False,
    }


def _base_kwargs(repo_root, site, profile, scenarios, solver, model_python):
    ref = site.profiles[profile]
    options = {
        "repo_root": repo_root, "input_csv": ref.path,
        "scenarios": scenarios, "solver": solver,
        "profile_id": profile, "study_id": site.study_id,
        "site_id": site.site_id, "runner_kind": site.runner_kind,
        "can_run": site.can_run, "source_metadata": ref.metadata_path,
        "model_python": model_python,
    }
    if site.runner_kind == "eu":
        options["design_json"] = site.design_path
    elif site.runner_kind == "legacy":
        archived = site.metadata["baseline_metadata"]["model_parameters"]
        uniform = archived["technologies.pv.real_wacc_fraction"]
        options.update(uniform_wacc_percent=100 * float(uniform["value"]),
                       uniform_wacc_source=uniform.get("source"),
                       source_note=uniform.get("note", ""))
    return options


def _profile_input_receipt(site, profiles):
    """Prove that categorical OAT changes delivery timing at a fixed quantity."""
    frames = {profile: pd.read_csv(site.profiles[profile].path, dtype=str,
                                  keep_default_na=False) for profile in profiles}
    first_profile = profiles[0]
    reference = frames[first_profile]
    if "h2_demand" not in reference:
        raise ValueError("Lieferprofil-Input enthält keine H₂-Nachfrage.")
    annual = float(pd.to_numeric(reference["h2_demand"], errors="raise").sum())
    for profile, frame in frames.items():
        if list(frame.columns) != list(reference.columns) or not frame.drop(
                columns="h2_demand").equals(reference.drop(columns="h2_demand")):
            raise ValueError("Lieferprofil-OAT erfordert identische übrige Stundeninputs.")
        demand = pd.to_numeric(frame["h2_demand"], errors="raise")
        if not all(math.isfinite(float(value)) and float(value) >= 0 for value in demand):
            raise ValueError("Lieferprofil enthält ungültige H₂-Nachfragewerte.")
        if not math.isclose(float(demand.sum()), annual, rel_tol=1e-10, abs_tol=1e-6):
            raise ValueError("Lieferprofil-OAT erfordert dieselbe H₂-Jahresmenge.")
    if not math.isfinite(annual) or annual <= 0:
        raise ValueError("Lieferprofil-OAT benötigt eine positive H₂-Jahresmenge.")
    return {"profiles_checked": list(profiles), "annual_h2_requested_kg": annual,
            "unchanged_hourly_input_columns": [column for column in reference
                                                if column != "h2_demand"],
            "checks": "identical_non_demand_columns_and_equal_annual_demand"}


def build_oat_profile_plan(repo_root, site, base_profiles, scenarios,
                           solver="scipy-highs", *, variants=(),
                           profile_levels=(), compare_solvers=False,
                           model_python=None):
    """Compose existing native plans without introducing factorial cases.

    Each requested basis profile is an explicit parallel numeric OAT context.
    Alternative profile levels have unchanged scientific parameters. A profile
    baseline already present in a numeric context is computed only once.
    """
    scope = oat_profile_scope(base_profiles, scenarios, variants, profile_levels,
                              compare_solvers=compare_solvers)
    for profile in scope["base_profiles"] + scope["profile_levels"]:
        if profile not in site.profiles:
            raise ValueError("Lieferprofil gehört nicht zum gewählten Standort.")
    profile_receipt = None
    if scope["profile_levels"]:
        profile_receipt = _profile_input_receipt(
            site, list(dict.fromkeys(scope["base_profiles"] + scope["profile_levels"])))
    parameter_names = model_adapter.supported_parameters(repo_root, model_python)
    supported = sensitivity_parameter_choices(parameter_names, site)
    for variant in scope["variants"]:
        if variant.get("parameter") not in supported:
            raise ValueError("Sensitivitätsparameter ist für diese Fallstudie nicht freigegeben.")
    plans = []
    backends = ["scipy-highs", "gurobi"] if compare_solvers else [solver]
    for backend in backends:
        for profile in scope["base_profiles"] + scope["profile_only_levels"]:
            numeric_context = profile in scope["base_profiles"]
            options = _base_kwargs(repo_root, site, profile, scope["scenarios"],
                                   backend, model_python)
            if numeric_context and scope["variants"]:
                child = model_adapter.build_sensitivity_plan(
                    **options, variants=scope["variants"])
            else:
                child = model_adapter.build_single_plan(**options)
            child["gui_context"] = {
                "study_id": site.study_id, "site_id": site.site_id,
                "profile": profile, "year_roles": site.year_roles,
                "historical": site.historical,
            }
            child["gui_oat_design"] = {
                "role": "numeric_base_context" if numeric_context else "profile_only_level",
                "base_profiles": scope["base_profiles"],
                "profile_parameter": PROFILE_PARAMETER if scope["profile_levels"] else None,
                "profile_levels": scope["profile_levels"],
                "numeric_variants_crossed_with_profile_levels": False,
            }
            plans.append(child)
    combined = model_adapter.combine_plans(plans)
    combined["gui_oat_design"] = {**scope,
        "profile_parameter": PROFILE_PARAMETER if scope["profile_levels"] else None,
        "profile_input_receipt": profile_receipt}
    if combined["optimization_count"] != scope["optimization_count"]:
        raise ValueError("Sichtbare OAT-Laufanzahl und nativer Auftrag stimmen nicht überein.")
    return combined
