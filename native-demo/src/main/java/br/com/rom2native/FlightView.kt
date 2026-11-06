package br.com.rom2native

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.min

/** 320x240 pixels produced by our C++ motor, not by a SNES emulator. */
class FlightView(context:Context,private val buttons:()->Int):View(context) {
    private val frame=IntArray(320*240)
    private val image=Bitmap.createBitmap(320,240,Bitmap.Config.ARGB_8888)
    private val paint=Paint(3)
    private val text=Paint(3).apply { color=Color.WHITE;textSize=27f;textAlign=Paint.Align.CENTER }
    private val hudPaint=Paint(3).apply {
        color=Color.WHITE
        textAlign=Paint.Align.LEFT
        typeface=android.graphics.Typeface.DEFAULT_BOLD
    }
    var loaded=false
    var touchMask=0
    private var lastFrame=System.nanoTime()
    override fun onDraw(canvas:Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)
        if(loaded) {
            val now=System.nanoTime()
            val elapsed=((now-lastFrame)/1_000_000_000f).coerceIn(0f,0.05f)
            lastFrame=now
            NativeEngine.step(buttons(),elapsed)
            NativeEngine.draw(frame)
            image.setPixels(frame,0,320,0,0,320,240)
            val aspect=4f/3f
            var w=height*aspect
            var h=height.toFloat()
            if(w>width){w=width.toFloat();h=w/aspect}
            canvas.drawBitmap(image,null,RectF((width-w)/2f,(height-h)/2f,(width+w)/2f,(height+h)/2f),paint)
            val stats=NativeEngine.missionStats()
            val hp=stats.getOrElse(0){0}
            val kills=stats.getOrElse(1){0}
            val total=stats.getOrElse(2){4}
            val mode=stats.getOrElse(3){0}
            val size=min(height*.048f,37f).coerceAtLeast(17f)
            hudPaint.textSize=size
            paint.color=0xda131b20.toInt()
            canvas.drawRoundRect(9f,8f,width*.54f,size*1.9f,12f,12f,paint)
            canvas.drawRoundRect(width*.81f,8f,width-9f,size*1.9f,12f,12f,paint)
            hudPaint.color=Color.WHITE
            canvas.drawText("VIDA $hp  |  ALVOS $kills/$total",20f,size*1.38f,hudPaint)
            hudPaint.textAlign=Paint.Align.CENTER
            canvas.drawText("REINICIAR",width*.9f,size*1.38f,hudPaint)
            hudPaint.textAlign=Paint.Align.LEFT
            if(mode!=0) {
                paint.color=0xe9121920.toInt()
                canvas.drawRoundRect(width*.20f,height*.39f,
                    width*.80f,height*.59f,16f,16f,paint)
                hudPaint.textSize=min(height*.064f,56f).coerceAtLeast(19f)
                hudPaint.textAlign=Paint.Align.CENTER
                val message=if(mode==1) "OBJETIVO CONCLUIDO" else "HELICOPTERO ABATIDO"
                canvas.drawText(message,width*.5f,height*.475f,hudPaint)
                hudPaint.textSize=min(height*.032f,27f).coerceAtLeast(13f)
                canvas.drawText("TOQUE REINICIAR PARA JOGAR NOVAMENTE",
                    width*.5f,height*.535f,hudPaint)
                hudPaint.textAlign=Paint.Align.LEFT
            }
        } else {
            text.textSize=30f
            canvas.drawText("IMPORTE A ROM ORIGINAL PARA TESTAR O MOTOR NATIVO",width/2f,height/2f,text)
        }
        val r=min(height*.15f,width*.07f)
        paint.color=0x99707989.toInt()
        val dx=width*.17f;val dy=height*.72f
        for((label,x,y) in listOf(Triple("↑",dx,dy-r),Triple("↓",dx,dy+r),
            Triple("←",dx-r,dy),Triple("→",dx+r,dy),Triple("FIRE",width*.83f,dy))) {
            val radius=if(label=="FIRE")r else r*.72f
            canvas.drawCircle(x,y,radius,paint)
            text.textSize=if(label=="FIRE")r*.44f else r*.65f
            canvas.drawText(label,x,y+text.textSize*.3f,text)
        }
        paint.color=Color.WHITE
        postInvalidateDelayed(33)
    }
    override fun onTouchEvent(e:MotionEvent):Boolean {
        if(e.actionMasked==MotionEvent.ACTION_UP && loaded &&
            e.getX(0)>=width*.80f && e.getY(0)<=height*.16f) {
            (context as? MainActivity)?.restartMission()
            return true
        }
        var mask=0
        val r=min(height*.15f,width*.07f)
        val dx=width*.17f;val dy=height*.72f
        for (i in 0 until e.pointerCount) {
            if(e.actionMasked==MotionEvent.ACTION_CANCEL ||
                (e.actionMasked==MotionEvent.ACTION_UP && e.actionIndex==i) ||
                (e.actionMasked==MotionEvent.ACTION_POINTER_UP && e.actionIndex==i))continue
            val x=e.getX(i);val y=e.getY(i)
            fun hit(cx:Float,cy:Float,rad:Float):Boolean {
                val ax=x-cx;val ay=y-cy
                return ax*ax+ay*ay<=rad*rad
            }
            if(hit(dx,dy-r,r*.86f))mask=mask or (1 shl 4)
            if(hit(dx,dy+r,r*.86f))mask=mask or (1 shl 5)
            if(hit(dx-r,dy,r*.86f))mask=mask or (1 shl 6)
            if(hit(dx+r,dy,r*.86f))mask=mask or (1 shl 7)
            if(hit(width*.83f,dy,r*1.15f))mask=mask or 1
        }
        touchMask=mask
        (context as? MainActivity)?.setTouchMask(mask)
        return true
    }
}
