"""Actual GPU vector addition via CUDA Driver API; no CPU fallback or nvcc required.

Uses driver JIT compilation of PTX, then compares every returned element on CPU.
Reference: https://docs.nvidia.com/cuda/cuda-driver-api/group__CUDA__EXEC.html
"""
import ctypes as C
import json
import time
import numpy as np

PTX = b'''
.version 6.4
.target sm_75
.address_size 64
.visible .entry vector_add(
    .param .u64 a, .param .u64 b, .param .u64 out, .param .u32 n
) {
    .reg .pred %p;
    .reg .b32 %r<5>;
    .reg .b64 %rd<8>;
    .reg .f32 %f<4>;
    ld.param.u64 %rd1, [a];
    ld.param.u64 %rd2, [b];
    ld.param.u64 %rd3, [out];
    ld.param.u32 %r1, [n];
    mov.u32 %r2, %ctaid.x;
    mov.u32 %r3, %ntid.x;
    mov.u32 %r4, %tid.x;
    mad.lo.u32 %r2, %r2, %r3, %r4;
    setp.ge.u32 %p, %r2, %r1;
    @%p bra DONE;
    mul.wide.u32 %rd4, %r2, 4;
    add.u64 %rd5, %rd1, %rd4;
    add.u64 %rd6, %rd2, %rd4;
    add.u64 %rd7, %rd3, %rd4;
    ld.global.f32 %f1, [%rd5];
    ld.global.f32 %f2, [%rd6];
    add.f32 %f3, %f1, %f2;
    st.global.f32 [%rd7], %f3;
DONE:
    ret;
}
'''


def main():
    cuda=C.CDLL('libcuda.so.1')
    ptr=C.c_void_p
    u64=C.c_uint64
    signatures={
        'cuInit':[C.c_uint], 'cuDeviceGet':[C.POINTER(C.c_int),C.c_int],
        'cuDeviceGetName':[ptr,C.c_int,C.c_int],
        'cuDevicePrimaryCtxRetain':[C.POINTER(ptr),C.c_int],
        'cuCtxSetCurrent':[ptr], 'cuDevicePrimaryCtxRelease_v2':[C.c_int],
        'cuModuleLoadData':[C.POINTER(ptr),ptr],
        'cuModuleGetFunction':[C.POINTER(ptr),ptr,C.c_char_p],
        'cuModuleUnload':[ptr], 'cuMemAlloc_v2':[C.POINTER(u64),C.c_size_t],
        'cuMemFree_v2':[u64], 'cuMemcpyHtoD_v2':[u64,ptr,C.c_size_t],
        'cuMemcpyDtoH_v2':[ptr,u64,C.c_size_t],
        'cuMemsetD8_v2':[u64,C.c_ubyte,C.c_size_t],
        'cuLaunchKernel':[ptr,*([C.c_uint]*7),ptr,C.POINTER(ptr),C.POINTER(ptr)],
        'cuCtxSynchronize':[], 'cuGetErrorName':[C.c_int,C.POINTER(C.c_char_p)],
    }
    for name, args in signatures.items():
        fn=getattr(cuda,name);fn.argtypes=args;fn.restype=C.c_int

    def call(name,*args):
        rc=getattr(cuda,name)(*args)
        if rc:
            error=C.c_char_p();cuda.cuGetErrorName(rc,C.byref(error))
            raise RuntimeError(f'{name}: {rc} {error.value!r}')

    call('cuInit',0)
    device=C.c_int();call('cuDeviceGet',C.byref(device),0)
    name=C.create_string_buffer(256);call('cuDeviceGetName',name,256,device)
    context=ptr();call('cuDevicePrimaryCtxRetain',C.byref(context),device)
    module=ptr();allocations=[]
    try:
        call('cuCtxSetCurrent',context)
        ptx=C.create_string_buffer(PTX)
        call('cuModuleLoadData',C.byref(module),ptx)
        kernel=ptr();call('cuModuleGetFunction',C.byref(kernel),module,b'vector_add')
        count=1048583  # Deliberately not a multiple of the block size.
        nbytes=count*4
        for _ in range(3):
            address=u64();call('cuMemAlloc_v2',C.byref(address),nbytes);allocations.append(address)
        a_dev,b_dev,out_dev=allocations
        n=C.c_uint(count)
        params=(ptr*4)(*[C.cast(C.byref(x),ptr) for x in (a_dev,b_dev,out_dev,n)])
        records=[]
        for seed in range(3):
            rng=np.random.default_rng(seed)
            a=rng.integers(-1000,1001,count).astype('float32')/4
            b=rng.integers(-1000,1001,count).astype('float32')/4
            out=np.empty(count,dtype='float32')
            call('cuMemcpyHtoD_v2',a_dev,ptr(a.ctypes.data),nbytes)
            call('cuMemcpyHtoD_v2',b_dev,ptr(b.ctypes.data),nbytes)
            call('cuMemsetD8_v2',out_dev,255,nbytes)
            start=time.perf_counter()
            call('cuLaunchKernel',kernel,(count+255)//256,1,1,256,1,1,0,None,params,None)
            call('cuCtxSynchronize')
            seconds=time.perf_counter()-start
            call('cuMemcpyDtoH_v2',ptr(out.ctypes.data),out_dev,nbytes)
            expected=a+b
            np.testing.assert_array_equal(out,expected)
            records.append({'seed':seed,'elements':count,'max_absolute_error':float(np.max(np.abs(out-expected))),
                            'launch_and_sync_seconds':seconds})
        print(json.dumps({'status':'PASS','device':name.value.decode(),'operation':'float32 vector addition',
                          'backend':'CUDA Driver API + PTX JIT','cpu_fallback':False,
                          'device_allocation_bytes':nbytes*3,'runs':records},indent=2))
    finally:
        for address in allocations:call('cuMemFree_v2',address)
        if module.value:call('cuModuleUnload',module)
        call('cuDevicePrimaryCtxRelease_v2',device)

if __name__=='__main__':
    main()
