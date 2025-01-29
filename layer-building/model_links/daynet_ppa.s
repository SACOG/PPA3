run pgm=network  
filei linki[1]=?_base.net
      linki[2]=vo.h07.net
      linki[3]=vo.h08.net
      linki[4]=vo.h09.net
      linki[5]=vo.md5.net
      linki[6]=vo.h15.net
      linki[7]=vo.h16.net
      linki[8]=vo.h17.net
      linki[9]=vo.ev2.net
      linki[10]=vo.n11.net


;if (capclass=7,99) delete
county='NA'
if (rad=1-29) county='Sacramento'
if (rad=30-36) county='Sutter'
if (rad=40-47) county='Yuba'
if (rad=50-57) county='Yolo'
if (rad=70-82) county='Placer'
if (rad=85-96) county='El Dorado'
if (rad=97) county='External'

lanemi=lanes*distance


; link volume by user type
h07v_da = li.2.V1_1 + li.2.V6_1 + li.2.V11_1
h07v_sd2 = li.2.V4_1 + li.2.V9_1 + li.2.V14_1
h07v_sd3 = li.2.V5_1 + li.2.V10_1 + li.2.V15_1
h07v_cv = li.2.V2_1 + li.2.V3_1 + li.2.V7_1 + li.2.V8_1 + li.2.V12_1 + li.2.V13_1
h07v = h07v_da + h07v_sd2 + h07v_sd3 + h07v_cv

h08v_da = li.3.V1_1 + li.3.V6_1 + li.3.V11_1
h08v_sd2 = li.3.V4_1 + li.3.V9_1 + li.3.V14_1
h08v_sd3 = li.3.V5_1 + li.3.V10_1 + li.3.V15_1
h08v_cv = li.3.V2_1 + li.3.V3_1 + li.3.V7_1 + li.3.V8_1 + li.3.V12_1 + li.3.V13_1
h08v = h08v_da + h08v_sd2 + h08v_sd3 + h08v_cv

h09v_da = li.4.V1_1 + li.4.V6_1 + li.4.V11_1
h09v_sd2 = li.4.V4_1 + li.4.V9_1 + li.4.V14_1
h09v_sd3 = li.4.V5_1 + li.4.V10_1 + li.4.V15_1
h09v_cv = li.4.V2_1 + li.4.V3_1 + li.4.V7_1 + li.4.V8_1 + li.4.V12_1 + li.4.V13_1
h09v = h09v_da + h09v_sd2 + h09v_sd3 + h09v_cv

md5v_da = li.5.V1_1 + li.5.V6_1 + li.5.V11_1
md5v_sd2 = li.5.V4_1 + li.5.V9_1 + li.5.V14_1
md5v_sd3 = li.5.V5_1 + li.5.V10_1 + li.5.V15_1
md5v_cv = li.5.V2_1 + li.5.V3_1 + li.5.V7_1 + li.5.V8_1 + li.5.V12_1 + li.5.V13_1
md5v = md5v_da + md5v_sd2 + md5v_sd3 + md5v_cv

h15v_da = li.6.V1_1 + li.6.V6_1 + li.6.V11_1
h15v_sd2 = li.6.V4_1 + li.6.V9_1 + li.6.V14_1
h15v_sd3 = li.6.V5_1 + li.6.V10_1 + li.6.V15_1
h15v_cv = li.6.V2_1 + li.6.V3_1 + li.6.V7_1 + li.6.V8_1 + li.6.V12_1 + li.6.V13_1
h15v = h15v_da + h15v_sd2 + h15v_sd3 + h15v_cv

h16v_da = li.7.V1_1 + li.7.V6_1 + li.7.V11_1
h16v_sd2 = li.7.V4_1 + li.7.V9_1 + li.7.V14_1
h16v_sd3 = li.7.V5_1 + li.7.V10_1 + li.7.V15_1
h16v_cv = li.7.V2_1 + li.7.V3_1 + li.7.V7_1 + li.7.V8_1 + li.7.V12_1 + li.7.V13_1
h16v = h16v_da + h16v_sd2 + h16v_sd3 + h16v_cv

h17v_da = li.8.V1_1 + li.8.V6_1 + li.8.V11_1
h17v_sd2 = li.8.V4_1 + li.8.V9_1 + li.8.V14_1
h17v_sd3 = li.8.V5_1 + li.8.V10_1 + li.8.V15_1
h17v_cv = li.8.V2_1 + li.8.V3_1 + li.8.V7_1 + li.8.V8_1 + li.8.V12_1 + li.8.V13_1
h17v = h17v_da + h17v_sd2 + h17v_sd3 + h17v_cv

ev2v_da = li.9.V1_1 + li.9.V6_1 + li.9.V11_1
ev2v_sd2 = li.9.V4_1 + li.9.V9_1 + li.9.V14_1
ev2v_sd3 = li.9.V5_1 + li.9.V10_1 + li.9.V15_1
ev2v_cv = li.9.V2_1 + li.9.V3_1 + li.9.V7_1 + li.9.V8_1 + li.9.V12_1 + li.9.V13_1
ev2v = ev2v_da + ev2v_sd2 + ev2v_sd3 + ev2v_cv

n11v_da = li.10.V1_1 + li.10.V6_1 + li.10.V11_1
n11v_sd2 = li.10.V4_1 + li.10.V9_1 + li.10.V14_1
n11v_sd3 = li.10.V5_1 + li.10.V10_1 + li.10.V15_1
n11v_cv = li.10.V2_1 + li.10.V3_1 + li.10.V7_1 + li.10.V8_1 + li.10.V12_1 + li.10.V13_1
n11v = n11v_da + n11v_sd2 + n11v_sd3 + n11v_cv


dyv_da = h07v_da + h08v_da + h09v_da + md5v_da + h15v_da + h16v_da + h17v_da + ev2v_da + n11v_da
dyv_sd2 = h07v_sd2 + h08v_sd2 + h09v_sd2 + md5v_sd2 + h15v_sd2 + h16v_sd2 + h17v_sd2 + ev2v_sd2 + n11v_sd2
dyv_sd3 = h07v_sd3 + h08v_sd3 + h09v_sd3 + md5v_sd3 + h15v_sd3 + h16v_sd3 + h17v_sd3 + ev2v_sd3 + n11v_sd3
dyv_cv = h07v_cv + h08v_cv + h09v_cv + md5v_cv + h15v_cv + h16v_cv + h17v_cv + ev2v_cv + n11v_cv

dyv = dyv_da + dyv_sd2 + dyv_sd3 + dyv_cv

; link v/c ratios
h07vc = li.2.vc_1
h08vc = li.3.vc_1
h09vc = li.4.vc_1
md5vc = li.5.vc_1
h15vc = li.6.vc_1
h16vc = li.7.vc_1
h17vc = li.8.vc_1
ev2vc = li.9.vc_1
n11vc = li.10.vc_1

; link vmt
h07vmt = h07v*distance
h08vmt = h08v*distance
h09vmt = h09v*distance
md5vmt = md5v*distance
h15vmt = h15v*distance
h16vmt = h16v*distance
h17vmt = h17v*distance
ev2vmt = ev2v*distance
n11vmt = n11v*distance

a3vmt=h07vmt+h08vmt+h09vmt
mdvmt=md5vmt
p3vmt=h15vmt+h16vmt+h17vmt
evvmt=ev2vmt+n11vmt
dayvmt=a3vmt+p3vmt+mdvmt+evvmt
; link volume & vmt for high v/c > 1.0
h07cvmt=0
h08cvmt=0
h09cvmt=0
md5cvmt=0
h15cvmt=0
h16cvmt=0
h17cvmt=0
ev2cvmt=0
n11cvmt=0

a3cvmt=0
p3cvmt=0
mdcvmt=0
evcvmt=0
daycvmt=0

h07cv=0
h08cv=0
h09cv=0
md5cv=0
h15cv=0
h16cv=0
h17cv=0
ev2cv=0
n11cv=0

a3cv=0
p3cv=0
mdcv=0
evcv=0
daycv=0
if(h07vc>1.0)
   h07cvmt=h07vmt
endif
if(h08vc>1.0)
   h08cvmt=h08vmt
endif
if(h09vc>1.0)
   h09cvmt=h09vmt
endif
if(md5vc>1.0)
   md5cvmt=md5vmt
endif
if(h15vc>1.0)
   h15cvmt=h15vmt
endif
if(h16vc>1.0)
   h16cvmt=h16vmt
endif
if(h17vc>1.0)
   h17cvmt=h17vmt
endif
if(ev2vc>1.0)
   ev2cvmt=ev2vmt
endif
if(n11vc>1.0)
   n11cvmt=n11vmt
endif

a3cvmt=h07cvmt+h08cvmt+h09cvmt
mdcvmt=md5cvmt
p3cvmt=h15cvmt+h16cvmt+h17cvmt
evcvmt=ev2cvmt+n11cvmt

daycvmt=a3cvmt+p3cvmt+mdcvmt+evcvmt

fileo neto=?daynet_ppa.net,
			INCLUDE=A B NAME DISTANCE CAPCLASS LANES SPEED LANEMI,
					DAYVMT DAYCVMT DYV_DA DYV_SD2 DYV_SD3 DYV_CV DYV

merge record=false
endrun





