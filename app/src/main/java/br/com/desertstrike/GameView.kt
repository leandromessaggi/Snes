package br.com.desertstrike

import android.content.Context
import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.Rect
import android.graphics.RectF
import android.view.MotionEvent
import android.view.View
import kotlin.math.abs
import kotlin.math.min

object Pad {
    const val B = 0; const val Y = 1; const val SELECT = 2; const val START = 3
    const val UP = 4; const val DOWN = 5; const val LEFT = 6; const val RIGHT = 7
    const val A = 8; const val X = 9; const val L = 10; const val R = 11
    fun bit(id: Int) = 1 shl id
}

class GameView(context: Context, private val menu: () -> Unit, private val touchChange: (Int) -> Unit) : View(context) {
    private val px = IntArray(512*512)
    private val guard = Any()
    private val imagePaint = Paint(Paint.FILTER_BITMAP_FLAG)
    private val padPaint = Paint(3).apply { color = 0x80607090.toInt() }
    private val labelPaint = Paint(3).apply { color = Color.WHITE; textAlign = Paint.Align.CENTER; typeface = android.graphics.Typeface.DEFAULT_BOLD }
    private var frame: Bitmap? = null
    private var frameW = 0
    private var frameH = 0
    var touchVisible = true
        set(v) { field = v; if (!v) touchChange(0); postInvalidate() }
    private data class Button(val id: Int, val title: String, val x: Float, val y: Float, val radius: Float)
    private fun controls(): List<Button> {
        val w = width.toFloat(); val h = height.toFloat(); val r = min(h*.093f, w*.06f)
        val leftX = w*.155f; val leftY = h*.72f
        val rightX = w*.81f; val rightY = h*.73f
        return listOf(
            Button(Pad.UP, "↑", leftX, leftY-r*1.02f, r*.92f),
            Button(Pad.DOWN, "↓", leftX, leftY+r*1.02f, r*.92f),
            Button(Pad.LEFT, "←", leftX-r*1.02f, leftY, r*.92f),
            Button(Pad.RIGHT, "→", leftX+r*1.02f, leftY, r*.92f),
            Button(Pad.Y, "Y", rightX-r*1.13f, rightY, r*.9f),
            Button(Pad.A, "A", rightX+r*1.13f, rightY, r*.9f),
            Button(Pad.X, "X", rightX, rightY-r*1.1f, r*.9f),
            Button(Pad.B, "B", rightX, rightY+r*1.1f, r*.9f),
            Button(Pad.L, "L", w*.13f, h*.26f, r),
            Button(Pad.R, "R", w*.87f, h*.26f, r),
            Button(Pad.SELECT, "SEL", w*.44f, h*.88f, r*.7f),
            Button(Pad.START, "STA", w*.56f, h*.88f, r*.7f)
        )
    }
    fun updateFrame(encoded: Int) {
        val w = encoded and 0xffff; val h = encoded ushr 16
        if (w !in 1..512 || h !in 1..512) return
        synchronized(guard) {
            if (frameW != w || frameH != h) {
                frame?.recycle()
                frame = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)
                frameW = w; frameH = h
            }
            frame?.setPixels(px,0,w,0,0,w,h)
        }
        postInvalidate()
    }
    fun pixelBuffer(): IntArray = px
    override fun onDraw(canvas: Canvas) {
        super.onDraw(canvas)
        canvas.drawColor(Color.BLACK)
        synchronized(guard) {
            frame?.let { b ->
                val aspect = 4f/3f
                var targetH = height.toFloat()
                var targetW = targetH*aspect
                if (targetW > width) { targetW = width.toFloat(); targetH = targetW/aspect }
                val dx = (width-targetW)/2f; val dy=(height-targetH)/2f
                canvas.drawBitmap(b, Rect(0,0,frameW,frameH), RectF(dx,dy,dx+targetW,dy+targetH), imagePaint)
            }
        }
        if (touchVisible) {
            for (b in controls()) {
                canvas.drawCircle(b.x,b.y,b.radius,padPaint)
                labelPaint.textSize=b.radius*.62f
                canvas.drawText(b.title,b.x,b.y + labelPaint.textSize*.33f,labelPaint)
            }
        }
        padPaint.color = 0xa0202834.toInt()
        val buttonRadius = min(height*.065f,width*.045f)
        canvas.drawRoundRect(RectF(width-buttonRadius*2.4f,10f,width-8f,buttonRadius*1.8f),12f,12f,padPaint)
        labelPaint.textSize=buttonRadius*.7f
        canvas.drawText("☰",width-buttonRadius*1.25f,buttonRadius*1.1f,labelPaint)
        padPaint.color = 0x80607090.toInt()
    }
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN || event.actionMasked == MotionEvent.ACTION_POINTER_DOWN) {
            val idx = event.actionIndex
            val radius = min(height*.065f,width*.045f)
            if (event.getX(idx) > width-radius*2.5f && event.getY(idx) < radius*2.1f) {
                touchChange(0); menu(); return true
            }
        }
        var result = 0
        if (touchVisible) {
            val buttons=controls()
            for (i in 0 until event.pointerCount) {
                if ((event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_POINTER_UP) && event.actionIndex == i) continue
                if (event.actionMasked == MotionEvent.ACTION_CANCEL) continue
                val x=event.getX(i); val y=event.getY(i)
                buttons.forEach { b ->
                    if (abs(x-b.x) <= b.radius*1.17f && abs(y-b.y) <= b.radius*1.17f &&
                        (x-b.x)*(x-b.x)+(y-b.y)*(y-b.y) <= b.radius*b.radius*1.37f) result = result or Pad.bit(b.id)
                }
            }
        }
        touchChange(result)
        return true
    }
}
