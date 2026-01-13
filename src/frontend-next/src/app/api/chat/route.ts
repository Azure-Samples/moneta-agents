import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const backendUrl = process.env.BACKEND_ENDPOINT || "http://localhost:8000";

  try {
    const body = await request.json();

    const response = await fetch(`${backendUrl}/http_trigger`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        // Forward auth headers if present
        ...(request.headers.get("x-ms-client-principal-id") && {
          "x-ms-client-principal-id": request.headers.get(
            "x-ms-client-principal-id"
          )!,
        }),
        ...(request.headers.get("x-ms-client-principal") && {
          "x-ms-client-principal": request.headers.get(
            "x-ms-client-principal"
          )!,
        }),
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      return NextResponse.json(
        { error: `Backend error: ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error("API proxy error:", error);
    return NextResponse.json(
      { error: "Failed to connect to backend" },
      { status: 500 }
    );
  }
}
