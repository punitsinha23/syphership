import Timeline from "@mui/lab/Timeline";
import TimelineItem from "@mui/lab/TimelineItem";
import TimelineSeparator from "@mui/lab/TimelineSeparator";
import TimelineConnector from "@mui/lab/TimelineConnector";
import TimelineContent from "@mui/lab/TimelineContent";
import TimelineDot from "@mui/lab/TimelineDot";

const stages = ["QUEUED", "BUILDING", "DEPLOYING", "RUNNING"];

export default function DeploymentTimeline({ status }) {
  const currentIndex = stages.indexOf(status);
  const isFailed = status === "FAILED";

  return (
    <Timeline position="alternate">
      {stages.map((stage, index) => {
        const completed = index < currentIndex;
        const active = index === currentIndex;

        return (
          <TimelineItem key={stage}>
            <TimelineSeparator>
              <TimelineDot
                color={completed || active ? "success" : "grey"}
                variant={active ? "filled" : "outlined"}
              />

              {index < stages.length - 1 && (
                <TimelineConnector
                  sx={{
                    bgcolor: completed ? "success.main" : "grey.400",
                  }}
                />
              )}
            </TimelineSeparator>

            <TimelineContent>{stage}</TimelineContent>
          </TimelineItem>
        );
      })}

      {isFailed && (
        <TimelineItem>
          <TimelineSeparator>
            <TimelineDot color="error" variant="filled" />
          </TimelineSeparator>

          <TimelineContent>
            <strong>FAILED</strong>
          </TimelineContent>
        </TimelineItem>
      )}
    </Timeline>
  );
}

