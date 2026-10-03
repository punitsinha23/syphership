export function generateMockSha(){
    return Array.from(
        { length: 40 },
        () => Math.floor(Math.random()* 16).toString(16)
    ).join("")
}