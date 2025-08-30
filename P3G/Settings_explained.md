# Primer3 Settings Guide

This page explains the settings available in P3G in an easier to follow terms based on the original and more expansive explanation found [here](https://bioinfo.ut.ee/primer3-0.4.0/input-help.htm).

## General Notes

Before using Primer3, make sure your input sequence is clean:

- Remove potential vector sequences and/or cloning artifacts
- Avoid using sequences that are artificially made if these are not representative of the actual sequence you are trying to detect
- Screen for repetitive sequences that you want to avoid

When using sequenced data and there are low-quality bases present, these can be changed into N's or marked as **Excluded regions** in the application itself. Use of the **Included Region** can also be used to focus Primer on the good part of your sequence.  

## Core Settings

- **Source Sequence**: The DNA sequence used for primer design.  
- **Sequence ID**: An identifier carried into the output.  
- **Pick Primers Checkboxes**: Options to tell Primer3 whether to generate:  
  - Forward primer  
  - Reverse primer  
  - Probe (internal oligo)  
  - Or allow user-provided sequences  

- **Target Sequences**: Regions that the primers must flank, and would thus be amplified in PCR (e.g. repeat or SNP). Format: `start,length`.  
- **Excluded Regions**: Regions primers may not overlap (low quality or repeats). Format: `start,length`.  
- **Product Size Range**: Allowed product length ranges, e.g. `150-250 300-400`.  Primer3 will first try to pick primers in the first range, and if it fails move on to the second and so on until the specified number of primers are selected or has run out of ranges.
- **Number of Primers to Return**: Maximum pairs returned, sorted by quality depending on penalty settings. Do note that a specific primer can appear multiple times in different pairs (e.g. Forward primer 1 can appear with Reverse 1 and Reverse 2).  
- **Max 3′ Stability**: Maximum duplex stability for the last 5 bases at the 3′ end (kcal/mol), with a bigger number representing a higher stability. THis is calculated using THe Nearest-Neighbor parameter values specified by the "Thermodynamic Table Parameters" setting.
- **Max Repeat Mispriming**: Maximum allowed similarity with repeat library sequences from Mispriming Libraries.  
- **Max Template Mispriming**: Maximum similarity to unintended sites in the source sequence.  
- **Max Pair Repeat Mispriming**: Combined mispriming score for both primers against s Mispriming Library.
- **Max Pair Template Mispriming**: Combined mispriming score for both primers within the template.  

---

## General Primer Picking

- **Primer Size**: Minimum, optimum, maximum length (1–36 bases).  
- **Primer Tm**: Minimum, optimum, maximum melting temperature.  
- **Product Tm**: Minimum, optimum, maximum melting temperature of the PCR product.  
- **Primer GC%**: Minimum, optimum, maximum GC content.  
- **Max Tm Difference**: Maximum difference between left and right primer Tm.  
- **Thermodynamic Parameters Table**:  Option for the Nearest-Neighbor thermodynamic parameters for melting temperature calculation. Two different tables are available
  - Breslauer et al. 1986 (default, for backward compatibility)  
  - SantaLucia 1998 (recommended)  

- **Max Self-Complementarity**: Limit for a primer to bind to itself or another primer anywhere along the primers. For lowering primer dimer risk.
- **Max 3′ Self-Complementarity**: Limit for primers to bind at the 3' end. Binding at the 3′ end can be especially problematic as DNA polymerases extend from the 3' end, and could lead to primer dimer amplification.  
- **Max Ns in Primer**: Maximum unknown bases (`N`) allowed.  
- **Max Poly-X**: Maximum consecutive identical bases (e.g. AAAAA).  
- **Inside Target Penalty**: Penalty weight for primers overlapping the target.  
- **Outside Target Penalty**: Penalty weight for primers near but not overlapping the target.  
- **First Base Index**: Set `1` for GenBank-style (default), or `0` for zero-based.  
- **CG Clamp**: Require the specified number of Gs and Cs at the 3' end of both primers. Does not affect the hybridization oligo / probe if one is requested.

- **Monovalent Salt Concentrations**: The millimolar (mM) concentration of salt (usually KCl) in the PCR reaction, and is used to calculate oligo melting temperatures.
- **Divalent Salt Concentrations**: The millimolar concentration of divalent salt cations (usually MgCl²⁺) in the PCR reaction. Primer3 converts the concentration of divalent cations to monovalent cations using the following formula from [Ahsen et al., 2001](www.clinchem.org/cgi/content/full/47/11/1956):

    ```
    [Monovalent cations] = [Monovalent cations] + 120*(√([divalent cations] - [dNTP])) 
    ```

- **dNTP Concentration**: The millimolar concentrations of deoxyribonucleotide triphosphate. Needed if divalent ions are set.  
- **Salt Correction Formula**:  Option to set the specific salt correction formula for calculating the melting temperatures:
  - [Schildkraut 1965](https://onlinelibrary.wiley.com/doi/10.1002/bip.360030207)  (set as default for backward compatibility)
  - [SantaLucia 1998](https://www.pnas.org/doi/full/10.1073/pnas.95.4.1460) (recommended)  
  - [Owczarzy 2004](https://pubs.acs.org/doi/10.1021/bi034621r)

- **Annealing Oligo Concentration**: The nanomolar (nM) concentration of annealing oligos in the PCR reaction, is used to calculate oligo melting temperatures.  

- **Ambiguity / Masking Checkboxes**:  
  - **Liberal Base**: Allow Primer3 to accept IUB/IUPAC codes for bases by changing all unrecognized bases to 'N'. You will need to increase the 'Max Ns Accepted' setting to allow primers with Ns.
  - **Consensus Mode**:Currently not implemented. Effects in practice: If left unchecked (default), ambiguity codes in mispriming/repeat libraries are treated as consensus, so R matches both A and G, making mispriming detection more permissive. If checked, ambiguity codes are treated literally, so R only matches R, reducing the number of flagged sites. When to use: Leave it unchecked if you want safer, broader mispriming detection (the usual case). Enable it only if your library uses ambiguity codes for annotation purposes or if the broad matching is excluding too many valid primers.
  - **Lowercase Masking**:Enabling lowercase masking allows primers to overlap lowercase regions in the sequence (usually repeats or other problematic sequences) except for the 3' end, preventing primers from starting or ending in these regions while still using nearby sequence. Lowercase regions would be used to show where there are less preferential regions to design oligos around.

---

## Internal Oligo (Probe) Picking

- **Probe Size**: Minimum, optimum, maximum probe length.  
- **Probe Tm**: Minimum, optimum, maximum melting temperature.  
- **Probe GC%**: Minimum, optimum, maximum GC content.  
- **Max Probe Self-Complementarity** : Limit for a probe to bind to itself in the PCR reaction.
- **Max Probe 3′ Self-Complementarity**: The maximum limit a probe bind to the 3' end of another probe, although this is meaningless in single probe hybridization setting, since primer-dimer or probe-dimers should not occur. Recommended to set to the same value as the Max Probe Self-Complementarity.
- **Max Ns in Probe**: Maximum unknown bases (`N`) in the probe sequence  
- **Max Probe Poly-X**: Maximum consecutive identical bases in the probe (e.g. AAAAA)
- **Probe Salt Concentrations**: Monovalent and divalent cations, same as for the primers.
- **Probe dNTP Concentration** : Same as for the primers.
- **Probe Oligo Concentration**: Same as for the primers.

---
