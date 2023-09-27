#ifndef _OPERATORS_SMV_KERNELS_PARAMS_H_
#define _OPERATORS_SMV_KERNELS_PARAMS_H_

#ifndef VECTOR_SIZE
#define VECTOR_SIZE 8
#elif VECTOR_SIZE != 8 //number of simd lanes
#error "Existing VECTOR_SIZE is incompatible with SMV!"
#endif

#define NUM_MACC_INSTS 8 // number of macs can do by 1 PE at same time
#define NUM_PE_INSTS 108 // number of PEs. different PEs are mapped to different output channels (weight kernels)

#define DATA_PE_ALIGNMENT (NUM_MACC_INSTS)*(VECTOR_SIZE)

#endif
