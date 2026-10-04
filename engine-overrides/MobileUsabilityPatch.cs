using Godot;
using MinorShift.Emuera;

public partial class EmueraContent
{
    internal bool mobileAutoScaleEnabled = true;

    public static int GetAndroidLogicalContentWidth(int safeWidth)
    {
        if (safeWidth <= 0)
            return 960;
        if (safeWidth <= 800)
            return safeWidth;
        if (safeWidth <= 1200)
            return 800;
        return 960;
    }

    internal Rect2 ExpandMobileConsoleHitRect(Rect2 rect)
    {
        if (!OS.HasFeature("mobile"))
            return rect;

        float visualScale = Mathf.Max(contentScale, 0.5f);
        float targetHeight = 52.0f / visualScale;
        float horizontalPadding = 7.0f / visualScale;
        float extraHeight = Mathf.Max(0.0f, targetHeight - rect.Size.Y);
        float verticalPadding = extraHeight * 0.5f;

        return new Rect2(
            rect.Position - new Vector2(horizontalPadding, verticalPadding),
            new Vector2(rect.Size.X + horizontalPadding * 2.0f, rect.Size.Y + extraHeight));
    }

    internal void ApplyMobileViewportScale()
    {
        if (!OS.HasFeature("mobile") || !mobileAutoScaleEnabled || ContentSafeWidth <= 0)
            return;

        float logicalWidth = Mathf.Max(Config.DrawableWidth + 3, 1);
        float targetScale = Mathf.Clamp(ContentSafeWidth / logicalWidth, 1.0f, 2.75f);
        SetContentScale(targetScale, false, true);
    }
}
