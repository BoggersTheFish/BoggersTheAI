from __future__ import annotations

import numpy as np

from tensionforge.runtime import TensionForgeRuntime
from tensionforge.tensor import DeviceTensor


WORKSPACE_BACKWARD_SOURCE = r"""
__kernel void add_fp32(__global const float *a, __global const float *b,
 __global float *o, const uint n) { uint i=get_global_id(0); if(i<n)o[i]=a[i]+b[i]; }
__kernel void fill_fp32(__global float *o,const float v,const uint n){uint i=get_global_id(0);if(i<n)o[i]=v;}
__kernel void scale_inplace_fp32(__global float *o,const float v,const uint n){uint i=get_global_id(0);if(i<n)o[i]*=v;}
__kernel void concat_backward_fp32(__global const float *g,__global float *gl,__global float *gr,
 const uint rows,const uint lc,const uint rc){uint i=get_global_id(0),c=lc+rc;if(i>=rows*c)return;
 uint r=i/c,j=i%c;if(j<lc)gl[r*lc+j]=g[i];else gr[r*rc+j-lc]=g[i];}
__kernel void broadcast_rows_backward_fp32(__global const float *g,__global float *x,
 const uint b,const uint rep,const uint f){uint i=get_global_id(0);if(i>=b*f)return;uint q=i/f,j=i%f;float s=0;
 for(uint k=0;k<rep;k++)s+=g[(q*rep+k)*f+j];x[i]=s;}
__kernel void table_row_backward_fp32(__global const float *g,__global float *table,
 const uint rows,const uint tr,const uint f,const uint chosen){uint i=get_global_id(0);if(i>=tr*f)return;float s=0;
 if(i/f==chosen)for(uint r=0;r<rows;r++)s+=g[r*f+i%f];table[i]=s;}
__kernel void gelu_backward_fp32(__global const float*x,__global const float*g,__global float*o,const uint n){
 uint i=get_global_id(0);if(i<n){float v=x[i];o[i]=g[i]*(0.5f*(1.0f+erf(v*0.7071067811865475f))
 +v*0.3989422804014327f*exp(-0.5f*v*v));}}
__kernel void layer_norm_backward_input_fp32(__global const float*x,__global const float*w,
 __global const float*g,__global float*gx,const uint rows,const uint c,const float eps){uint r=get_global_id(0);if(r>=rows)return;
 uint z=r*c;float m=0;for(uint j=0;j<c;j++)m+=x[z+j];m/=c;float v=0;for(uint j=0;j<c;j++){float d=x[z+j]-m;v+=d*d;}v/=c;
 float inv=rsqrt(v+eps),s1=0,s2=0;for(uint j=0;j<c;j++){float q=g[z+j]*w[j];s1+=q;s2+=q*(x[z+j]-m);}
 for(uint j=0;j<c;j++){float q=g[z+j]*w[j];gx[z+j]=inv*(q-s1/c-(x[z+j]-m)*inv*inv*s2/c);}}
__kernel void layer_norm_backward_param_fp32(__global const float*x,__global const float*g,
 __global float*gw,__global float*gb,const uint rows,const uint c,const float eps){uint j=get_global_id(0);if(j>=c)return;float sw=0,sb=0;
 for(uint r=0;r<rows;r++){uint z=r*c;float m=0;for(uint k=0;k<c;k++)m+=x[z+k];m/=c;float v=0;for(uint k=0;k<c;k++){float d=x[z+k]-m;v+=d*d;}v/=c;
 float q=g[z+j];sw+=q*(x[z+j]-m)*rsqrt(v+eps);sb+=q;}gw[j]=sw;gb[j]=sb;}
__kernel void softmax_backward_fp32(__global const float*y,__global const float*g,__global float*x,const uint rows,const uint c){
 uint r=get_global_id(0);if(r>=rows)return;uint z=r*c;float s=0;for(uint j=0;j<c;j++)s+=g[z+j]*y[z+j];for(uint j=0;j<c;j++)x[z+j]=y[z+j]*(g[z+j]-s);}
__kernel void reduce_backward_fp32(__global const float*x,__global const float*gm,__global const float*gx,
 __global float*o,const uint b,const uint n,const uint f){uint i=get_global_id(0);if(i>=b*n*f)return;uint q=i/(n*f),j=i%f;
 float best=x[(q*n)*f+j];uint arg=0;for(uint k=1;k<n;k++){float v=x[(q*n+k)*f+j];if(v>best){best=v;arg=k;}}
 o[i]=gm[q*f+j]/n+((i/f)%n==arg?gx[q*f+j]:0.0f);}
__kernel void gather_backward_fp32(__global const float*g,__global const int*idx,__global float*o,
 const uint b,const uint n,const uint k,const uint f,const uint shared){uint i=get_global_id(0),total=(shared?1:b)*n*f;if(i>=total)return;
 uint q=shared?0:i/(n*f),slot=(i/f)%n,j=i%f;float s=0;for(uint bb=shared?0:q;bb<(shared?b:q+1);bb++)for(uint p=0;p<k;p++)
 if((uint)idx[bb*k+p]==slot)s+=g[(bb*k+p)*f+j];o[i]=s;}
__kernel void scatter_backward_input_fp32(__global const float*g,__global const int*idx,__global float*o,
 const uint b,const uint n,const uint k,const uint f){uint i=get_global_id(0);if(i>=b*n*f)return;uint q=i/(n*f),s=(i/f)%n;int hit=0;
 for(uint p=0;p<k;p++)hit|=(uint)idx[q*k+p]==s;o[i]=hit?0:g[i];}
__kernel void scatter_backward_update_fp32(__global const float*g,__global const int*idx,__global float*o,
 const uint b,const uint n,const uint k,const uint f){uint i=get_global_id(0);if(i>=b*k*f)return;uint q=i/(k*f),p=(i/f)%k,j=i%f;
 o[i]=g[(q*n+(uint)idx[q*k+p])*f+j];}
__kernel void topk_backward_fp32(__global const float*g,__global const int*idx,__global float*o,
 const uint rows,const uint cols,const uint k){uint i=get_global_id(0);if(i>=rows*cols)return;uint r=i/cols,c=i%cols;float s=0;
 for(uint p=0;p<k;p++)if((uint)idx[r*k+p]==c)s+=g[r*k+p];o[i]=s;}
__kernel void row_norm_backward_fp32(__global const float*a,__global const float*b,__global const float*y,
 __global const float*g,__global float*ga,__global float*gb,const uint rows,const uint c){uint i=get_global_id(0);if(i>=rows*c)return;
 uint r=i/c;float q=y[r]>0?g[r]*(a[i]-b[i])/y[r]:0;ga[i]=q;gb[i]=-q;}
__kernel void tension_backward_fp32(__global const float*s,__global const float*p,__global const float*t,
 __global const float*g,__global float*gs,__global float*gp,__global float*gt,const uint rows,const uint c){uint i=get_global_id(0);if(i>=rows*c)return;
 uint r=i/c;gs[i]=g[i]*(1-t[r]);gp[i]=g[i]*t[r];if(i%c==0){float z=0;for(uint j=0;j<c;j++)z+=g[r*c+j]*(p[r*c+j]-s[r*c+j]);gt[r]=z;}}
__kernel void batched_dot_backward_fp32(__global const float*q,__global const float*v,__global const float*g,
 __global float*gq,__global float*gv,const uint b,const uint n,const uint f,const float scale){uint i=get_global_id(0);if(i>=b*n*f)return;
 uint bb=i/(n*f),slot=(i/f)%n,j=i%f;gv[i]=g[bb*n+slot]*q[bb*f+j]*scale;if(slot==0){float z=0;for(uint k=0;k<n;k++)z+=g[bb*n+k]*v[(bb*n+k)*f+j]*scale;gq[bb*f+j]=z;}}
__kernel void penalty_backward_fp32(__global const float*t,__global const float*g,__global float*gs,__global float*gt,const uint n){
 uint i=get_global_id(0);if(i<n){float v=t[i];gs[i]=g[i];gt[i]=(v>0.0f&&v<0.999f)?-g[i]/(1-v):0;}}
__kernel void weighted_backward_fp32(__global const float*w,__global const float*v,__global const float*g,
 __global float*gw,__global float*gv,const uint b,const uint n,const uint f){uint i=get_global_id(0);if(i>=b*n*f)return;
 uint bb=i/(n*f),slot=(i/f)%n,j=i%f;gv[i]=w[bb*n+slot]*g[bb*f+j];if(j==0){float z=0;for(uint k=0;k<f;k++)z+=g[bb*f+k]*v[(bb*n+slot)*f+k];gw[bb*n+slot]=z;}}
__kernel void embedding_backward_fp32(__global const int*ids,__global const float*g,__global float*gw,
 const uint count,const uint vocab,const uint f){uint i=get_global_id(0);if(i>=vocab*f)return;uint tok=i/f,j=i%f;float s=0;
 for(uint q=0;q<count;q++)if((uint)ids[q]==tok)s+=g[q*f+j];gw[i]=s;}
__kernel void embedding_forward_fp32(__global const int*ids,__global const float*w,__global float*o,const uint count,const uint f){
 uint i=get_global_id(0);if(i<count*f)o[i]=w[(uint)ids[i/f]*f+i%f];}
__kernel void cross_entropy_fp32(__global const float*x,__global const int*y,__global float*loss,__global float*g,
 const uint rows,const uint c){uint r=get_global_id(0);if(r>=rows)return;uint z=r*c;float m=-INFINITY;for(uint j=0;j<c;j++)m=fmax(m,x[z+j]);
 float s=0;for(uint j=0;j<c;j++)s+=exp(x[z+j]-m);float l=log(s)+m-x[z+(uint)y[r]];loss[r]=l/rows;
 for(uint j=0;j<c;j++)g[z+j]=(exp(x[z+j]-m)/s-(j==(uint)y[r]?1.0f:0.0f))/rows;}
__kernel void route_scores_fp32(__global const float*q,__global const float*k,__global float*o,
 const uint b,const uint n,const uint f,const float scale){uint i=get_global_id(0);if(i>=b*n)return;uint bb=i/n,s=i%n;float z=0;
 for(uint j=0;j<f;j++)z+=q[bb*f+j]*k[s*f+j];o[i]=z*scale;}
__kernel void route_backward_q_fp32(__global const float*k,__global const float*g,__global float*gq,
 const uint b,const uint n,const uint f,const float scale){uint i=get_global_id(0);if(i>=b*f)return;uint bb=i/f,j=i%f;float z=0;
 for(uint s=0;s<n;s++)z+=g[bb*n+s]*k[s*f+j];gq[i]=z*scale;}
__kernel void route_backward_k_fp32(__global const float*q,__global const float*g,__global float*gk,
 const uint b,const uint n,const uint f,const float scale){uint i=get_global_id(0);if(i>=n*f)return;uint s=i/f,j=i%f;float z=0;
 for(uint bb=0;bb<b;bb++)z+=g[bb*n+s]*q[bb*f+j];gk[i]=z*scale;}
__kernel void sum_squares_at_fp32(__global const float*x,__global float*parts,const uint slot,const uint n){
 if(get_global_id(0)==0){float s=0;for(uint i=0;i<n;i++)s+=x[i]*x[i];parts[slot]=s;}}
__kernel void finish_global_norm_fp32(__global const float*parts,__global float*norm,const uint count){
 if(get_global_id(0)==0){float s=0;for(uint i=0;i<count;i++)s+=parts[i];norm[0]=sqrt(s);}}
__kernel void clip_from_parts_fp32(__global float*x,__global const float*parts,const uint count,const float max_norm,const uint n){
 uint i=get_global_id(0);if(i>=n)return;float s=0;for(uint j=0;j<count;j++)s+=parts[j];float norm=sqrt(s);
 float scale=norm>max_norm?max_norm/(norm+1.0e-6f):1.0f;x[i]*=scale;}
__kernel void accumulate_sum_fp32(__global const float*x,__global float*sum,const uint n){
 if(get_global_id(0)==0){float value=0;for(uint i=0;i<n;i++)value+=x[i];sum[0]+=value;}}
__kernel void accumulate_index_counts_fp32(__global const int*indices,__global float*counts,const uint n,const uint slots){
 uint slot=get_global_id(0);if(slot>=slots)return;float value=0;for(uint i=0;i<n;i++)if((uint)indices[i]==slot)value+=1.0f;counts[slot]+=value;}
__kernel void auxiliary_loss_fp32(__global const float*sum,__global const float*counts,__global float*loss,
 const uint tension_count,const uint index_count,const uint slots,const float tension_weight,const float usage_weight){
 if(get_global_id(0)==0){float mean=sum[0]/tension_count;float balance=fmax(0.05f-mean,0.0f)+fmax(mean-0.95f,0.0f);float usage=0;
 for(uint i=0;i<slots;i++){float p=counts[i]/index_count;float d=p-1.0f/slots;usage+=d*d;}usage/=slots;
 loss[0]=tension_weight*balance+usage_weight*usage;}}
"""


def _check(runtime, tensor, name, dtype=np.float32):
    if tensor.runtime is not runtime: raise ValueError(f"{name} belongs to a different runtime")
    if tensor.dtype != np.dtype(dtype): raise ValueError(f"{name} must use {np.dtype(dtype)}")


def _out(runtime, shape, output=None, dtype=np.float32):
    if output is None: return DeviceTensor.empty(runtime, shape, dtype=dtype)
    _check(runtime, output, "output", dtype)
    if output.shape != shape: raise ValueError(f"output must have shape {shape}")
    return output


def _run(runtime, name, count, args):
    local=min(256,int(runtime.device.max_work_group_size)); kernel=runtime.kernel(WORKSPACE_BACKWARD_SOURCE,name)
    runtime.run_kernel(kernel,global_size=(runtime.round_up(count,local),),local_size=(local,),arguments=args)


def fill_device(runtime, shape, value=0.0, *, output=None):
    output=_out(runtime,shape,output); _run(runtime,"fill_fp32",output.size,(output.buffer,np.float32(value),np.uint32(output.size))); return output


def add_device(runtime, left, right, *, output=None):
    _check(runtime,left,"left");_check(runtime,right,"right")
    if left.shape!=right.shape: raise ValueError("add shapes must match")
    output=_out(runtime,left.shape,output);_run(runtime,"add_fp32",left.size,(left.buffer,right.buffer,output.buffer,np.uint32(left.size)));return output


def scale_inplace_device(runtime, tensor, scale):
    _check(runtime,tensor,"tensor");_run(runtime,"scale_inplace_fp32",tensor.size,(tensor.buffer,np.float32(scale),np.uint32(tensor.size)))


def concatenate_backward_device(runtime, grad, left_columns):
    _check(runtime,grad,"grad"); rows,cols=grad.shape; rc=cols-left_columns
    gl=_out(runtime,(rows,left_columns));gr=_out(runtime,(rows,rc));_run(runtime,"concat_backward_fp32",grad.size,(grad.buffer,gl.buffer,gr.buffer,np.uint32(rows),np.uint32(left_columns),np.uint32(rc)));return gl,gr


def broadcast_rows_backward_device(runtime, grad, batches, repeats):
    _check(runtime,grad,"grad");f=grad.shape[1];o=_out(runtime,(batches,f));_run(runtime,"broadcast_rows_backward_fp32",o.size,(grad.buffer,o.buffer,np.uint32(batches),np.uint32(repeats),np.uint32(f)));return o


def table_row_backward_device(runtime, grad, table_shape, row):
    _check(runtime,grad,"grad");o=_out(runtime,table_shape);_run(runtime,"table_row_backward_fp32",o.size,(grad.buffer,o.buffer,np.uint32(grad.shape[0]),np.uint32(table_shape[0]),np.uint32(table_shape[1]),np.uint32(row)));return o


def gelu_backward_device(runtime, inputs, grad):
    o=_out(runtime,inputs.shape);_run(runtime,"gelu_backward_fp32",o.size,(inputs.buffer,grad.buffer,o.buffer,np.uint32(o.size)));return o


def layer_norm_backward_device(runtime, inputs, weight, grad, epsilon=1e-5):
    rows=inputs.size//inputs.shape[-1];c=inputs.shape[-1];gx=_out(runtime,inputs.shape);gw=_out(runtime,(c,));gb=_out(runtime,(c,))
    _run(runtime,"layer_norm_backward_input_fp32",rows,(inputs.buffer,weight.buffer,grad.buffer,gx.buffer,np.uint32(rows),np.uint32(c),np.float32(epsilon)))
    _run(runtime,"layer_norm_backward_param_fp32",c,(inputs.buffer,grad.buffer,gw.buffer,gb.buffer,np.uint32(rows),np.uint32(c),np.float32(epsilon)));return gx,gw,gb


def softmax_backward_device(runtime, output, grad):
    rows=output.size//output.shape[-1];c=output.shape[-1];o=_out(runtime,output.shape);_run(runtime,"softmax_backward_fp32",rows,(output.buffer,grad.buffer,o.buffer,np.uint32(rows),np.uint32(c)));return o


def workspace_reduce_backward_device(runtime, workspace, grad_mean, grad_max):
    b,n,f=workspace.shape;o=_out(runtime,workspace.shape);_run(runtime,"reduce_backward_fp32",o.size,(workspace.buffer,grad_mean.buffer,grad_max.buffer,o.buffer,np.uint32(b),np.uint32(n),np.uint32(f)));return o


def gather_backward_device(runtime, grad, indices, input_shape, shared=False):
    b,k=indices.shape;n=input_shape[-2];f=input_shape[-1];o=_out(runtime,input_shape)
    _run(runtime,"gather_backward_fp32",o.size,(grad.buffer,indices.buffer,o.buffer,np.uint32(b),np.uint32(n),np.uint32(k),np.uint32(f),np.uint32(shared)));return o


def scatter_backward_device(runtime, grad, indices):
    b,n,f=grad.shape;k=indices.shape[1];gi=_out(runtime,grad.shape);gu=_out(runtime,(b,k,f))
    _run(runtime,"scatter_backward_input_fp32",gi.size,(grad.buffer,indices.buffer,gi.buffer,np.uint32(b),np.uint32(n),np.uint32(k),np.uint32(f)))
    _run(runtime,"scatter_backward_update_fp32",gu.size,(grad.buffer,indices.buffer,gu.buffer,np.uint32(b),np.uint32(n),np.uint32(k),np.uint32(f)));return gi,gu


def topk_backward_device(runtime, grad, indices, columns):
    rows,k=grad.shape;o=_out(runtime,(rows,columns));_run(runtime,"topk_backward_fp32",o.size,(grad.buffer,indices.buffer,o.buffer,np.uint32(rows),np.uint32(columns),np.uint32(k)));return o


def row_delta_norm_backward_device(runtime,left,right,output,grad):
    rows,c=left.shape;gl=_out(runtime,left.shape);gr=_out(runtime,right.shape);_run(runtime,"row_norm_backward_fp32",left.size,(left.buffer,right.buffer,output.buffer,grad.buffer,gl.buffer,gr.buffer,np.uint32(rows),np.uint32(c)));return gl,gr


def tension_update_broadcast_backward_device(runtime,state,proposal,tension,grad):
    rows,c=state.shape;gs=_out(runtime,state.shape);gp=_out(runtime,state.shape);gt=_out(runtime,tension.shape);_run(runtime,"tension_backward_fp32",state.size,(state.buffer,proposal.buffer,tension.buffer,grad.buffer,gs.buffer,gp.buffer,gt.buffer,np.uint32(rows),np.uint32(c)));return gs,gp,gt


def batched_dot_backward_device(runtime,query,slots,grad,scale=1.0):
    b,n,f=slots.shape;gq=_out(runtime,query.shape);gv=_out(runtime,slots.shape);_run(runtime,"batched_dot_backward_fp32",slots.size,(query.buffer,slots.buffer,grad.buffer,gq.buffer,gv.buffer,np.uint32(b),np.uint32(n),np.uint32(f),np.float32(scale)));return gq,gv


def tension_penalty_backward_device(runtime,tension,grad):
    gs=_out(runtime,grad.shape);gt=_out(runtime,tension.shape);_run(runtime,"penalty_backward_fp32",grad.size,(tension.buffer,grad.buffer,gs.buffer,gt.buffer,np.uint32(grad.size)));return gs,gt


def weighted_sum_backward_device(runtime,weights,values,grad):
    b,n,f=values.shape;gw=_out(runtime,weights.shape);gv=_out(runtime,values.shape);_run(runtime,"weighted_backward_fp32",values.size,(weights.buffer,values.buffer,grad.buffer,gw.buffer,gv.buffer,np.uint32(b),np.uint32(n),np.uint32(f)));return gw,gv


def embedding_forward_device(runtime,ids,weight,*,output=None):
    _check(runtime,ids,"ids",np.int32);count=ids.size;f=weight.shape[1];output=_out(runtime,ids.shape+(f,),output);_run(runtime,"embedding_forward_fp32",output.size,(ids.buffer,weight.buffer,output.buffer,np.uint32(count),np.uint32(f)));return output


def embedding_backward_device(runtime,ids,grad,weight_shape):
    o=_out(runtime,weight_shape);_run(runtime,"embedding_backward_fp32",o.size,(ids.buffer,grad.buffer,o.buffer,np.uint32(ids.size),np.uint32(weight_shape[0]),np.uint32(weight_shape[1])));return o


def cross_entropy_device(runtime,logits,targets):
    _check(runtime,targets,"targets",np.int32);rows,c=logits.shape;losses=_out(runtime,(rows,));grad=_out(runtime,logits.shape)
    _run(runtime,"cross_entropy_fp32",rows,(logits.buffer,targets.buffer,losses.buffer,grad.buffer,np.uint32(rows),np.uint32(c)));return losses,grad


def route_scores_device(runtime, query, keys, scale):
    b,f=query.shape;n=keys.shape[0];o=_out(runtime,(b,n));_run(runtime,"route_scores_fp32",o.size,(query.buffer,keys.buffer,o.buffer,np.uint32(b),np.uint32(n),np.uint32(f),np.float32(scale)));return o


def route_scores_backward_device(runtime, query, keys, grad, scale):
    b,f=query.shape;n=keys.shape[0];gq=_out(runtime,query.shape);gk=_out(runtime,keys.shape)
    _run(runtime,"route_backward_q_fp32",gq.size,(keys.buffer,grad.buffer,gq.buffer,np.uint32(b),np.uint32(n),np.uint32(f),np.float32(scale)))
    _run(runtime,"route_backward_k_fp32",gk.size,(query.buffer,grad.buffer,gk.buffer,np.uint32(b),np.uint32(n),np.uint32(f),np.float32(scale)));return gq,gk


def clip_gradients_device(runtime, gradients, max_norm=1.0):
    gradients=[gradient for gradient in gradients if gradient is not None]
    if not gradients: raise ValueError("at least one gradient is required")
    if max_norm <= 0: raise ValueError("max_norm must be positive")
    for gradient in gradients: _check(runtime,gradient,"gradient")
    parts=_out(runtime,(len(gradients),));norm=_out(runtime,(1,))
    for index,gradient in enumerate(gradients):
        _run(runtime,"sum_squares_at_fp32",1,(gradient.buffer,parts.buffer,np.uint32(index),np.uint32(gradient.size)))
    _run(runtime,"finish_global_norm_fp32",1,(parts.buffer,norm.buffer,np.uint32(len(gradients))))
    for gradient in gradients:
        _run(runtime,"clip_from_parts_fp32",gradient.size,(gradient.buffer,parts.buffer,np.uint32(len(gradients)),np.float32(max_norm),np.uint32(gradient.size)))
    return norm


def training_auxiliary_loss_device(runtime, pre_tensions, selected_indices, num_slots, tension_weight=.001, usage_weight=.001):
    pre_tensions=list(pre_tensions);selected_indices=list(selected_indices)
    if not pre_tensions or not selected_indices: raise ValueError("diagnostic tensors are required")
    total=fill_device(runtime,(1,));counts=fill_device(runtime,(num_slots,));loss=fill_device(runtime,(1,))
    tension_count=0;index_count=0
    for tensor in pre_tensions:
        _check(runtime,tensor,"pre_tension");tension_count+=tensor.size
        _run(runtime,"accumulate_sum_fp32",1,(tensor.buffer,total.buffer,np.uint32(tensor.size)))
    for tensor in selected_indices:
        _check(runtime,tensor,"selected_indices",np.int32);index_count+=tensor.size
        _run(runtime,"accumulate_index_counts_fp32",num_slots,(tensor.buffer,counts.buffer,np.uint32(tensor.size),np.uint32(num_slots)))
    _run(runtime,"auxiliary_loss_fp32",1,(total.buffer,counts.buffer,loss.buffer,np.uint32(tension_count),np.uint32(index_count),np.uint32(num_slots),np.float32(tension_weight),np.float32(usage_weight)))
    return loss
