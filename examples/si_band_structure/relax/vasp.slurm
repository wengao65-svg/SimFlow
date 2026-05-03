#!/bin/bash
#SBATCH -N 1
#SBATCH --ntasks-per-node=4
#SBATCH -c 8
#SBATCH -J Si-relax
#SBATCH --gres=dcu:4
#SBATCH -p kshdtest
#SBATCH -t 00:30:00

module purge
source /public/home/ac4iry5343/apprepo/vasp/6.4.2-dtk24.04_all_nohdf5/scripts/env.sh

VASP_EXE=vasp_std

config=config.${SLURM_JOB_ID}
echo -e "-genv OMP_NUM_THREADS 6 \c" > $config
for i in $(scontrol show hostnames $SLURM_NODELIST)
do
  for ((j=0; j<4; j++))
  do
    echo "-host $i -env HIP_VISIBLE_DEVICES $j -n 1 numactl --cpunodebind=$j --membind=$j $VASP_EXE" >> $config
  done
done

ulimit -s unlimited
export NCCL_IB_HCA="mlx5_0"
export HSA_FORCE_FINE_GRAIN_PCIE=1

mpirun -configfile $config
