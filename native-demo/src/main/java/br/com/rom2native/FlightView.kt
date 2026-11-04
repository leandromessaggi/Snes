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
