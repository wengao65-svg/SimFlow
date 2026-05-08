# LAMMPS Key Parameters Reference

## Essential Parameters

| Parameter | Description | Typical Range |
|-----------|-------------|---------------|
| units | Unit system | real, metal, si |
| timestep | Integration timestep (fs) | 0.5-2.0 |
| pair_style | Interatomic potential | Varies by system |
| run | Number of MD steps | 100000-10000000 |
| thermo | Thermo output interval | 100-1000 |
| dump | Trajectory output interval | 1000-10000 |

## Common Simulation Types

### NVE Equilibration
```
fix 1 all nve
run 100000
```

### NPT Equilibration
```
fix 1 all npt temp 300 300 100 iso 0 0 1000
run 200000
```

### NVT Production
```
fix 1 all nvt temp 300 300 100
run 1000000
```

## Common Force Fields

| System | pair_style | Notes |
|--------|-----------|-------|
| Metals | EAM/Alloy | Cu, Al, Ni, etc. |
| Water | TIP4P/2005 | SPC/E alternative |
| Organic | OPLS-AA | CHARMM alternative |
| Silica | Tersoff | SiO2 systems |
| Carbon | AIREBO | Graphene, CNT |

## Analysis Output

- RDF: compute rdf, fix ave/time
- MSD: compute msd
- Diffusion: linear fit of MSD vs time
- Temperature: thermo keyword temp
- Pressure: thermo keyword press
